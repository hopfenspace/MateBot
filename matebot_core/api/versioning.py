"""
MateBot API library to provide multiple versions of the API endpoints
"""

import logging
from typing import Callable, Dict, Iterable, Optional

import fastapi

from .. import schemas


VERSION_ANNOTATION_NAME = "_api_versions"
MAXIMAL_VERSION_ANNOTATION_NAME = "_maximal_api_version"
MINIMAL_VERSION_ANNOTATION_NAME = "_minimal_api_version"


def versions(
        *annotations: int,
        minimal: Optional[int] = None,
        maximal: Optional[int] = None
) -> Callable[[Callable], Callable]:
    """
    Decorate a path operation function with the version(s) of the API that should support it

    :param annotations: any number of explicit API versions that should include the decorated
        path operation (which can't be below or above the minimal and maximal values respectively)
    :param minimal: minimal version of APIs that should include the decorated path operation
    :param maximal: maximal version of APIs that should include the decorated path operation
    :return: decorator to use on a path operation function
    """

    if not all(map(lambda x: isinstance(x, int), annotations)):
        raise TypeError(f"Not all annotations are integers: {annotations!r}")
    if minimal:
        if not isinstance(minimal, int):
            raise TypeError(f"Expected int, got {type(minimal)!r}")
        if any(map(lambda x: x < minimal, annotations)):
            raise ValueError("Can't accept annotations smaller than the minimal version")
    if maximal:
        if not isinstance(maximal, int):
            raise TypeError(f"Expected int, got {type(minimal)!r}")
        if any(map(lambda x: x > maximal, annotations)):
            raise ValueError("Can't accept annotations bigger than the maximal version")

    def decorator(func: Callable) -> Callable:
        assert not hasattr(func, VERSION_ANNOTATION_NAME), "'versions' can't be used twice"
        assert not hasattr(func, MINIMAL_VERSION_ANNOTATION_NAME), "'versions' can't be used twice"
        assert not hasattr(func, MAXIMAL_VERSION_ANNOTATION_NAME), "'versions' can't be used twice"
        if annotations:
            setattr(func, VERSION_ANNOTATION_NAME, annotations)
        if minimal:
            setattr(func, MINIMAL_VERSION_ANNOTATION_NAME, minimal)
        if maximal:
            setattr(func, MAXIMAL_VERSION_ANNOTATION_NAME, maximal)
        return func

    return decorator


class VersionedFastAPI(fastapi.FastAPI):
    """
    Specialized FastAPI adding support for multiple versioned sub-APIs

    Use this class as in-place replacement for the previous FastAPI
    class. The constructor requires some new keyword arguments
    as well as the ``apis`` parameter which should be the definition
    which APIs should finally be loaded. Only API versions mentioned
    in this dictionary will be enabled later on during ``finish``.

    To add a new router to the API, use ``add_router`` instead
    of ``include_router``, since the latter would just add it and
    ignore the whole versioning part. After adding all the routers,
    call the ``finish`` method once to create and include the sub
    API definitions correctly with all path operations that were
    annotated to be included by the specific API version. It would
    be possible to omit certain API versions in the dictionary,
    those versions would obviously just be missing in the result.

    .. code-block::

        app = VersionedFastAPI(
            title="API",
            apis={
                1: FastAPI(
                    title="API v1",
                    version="1.0"
                ),
                2: FastAPI(
                    title="API v2",
                    version="2.0"
                )
            }
        )
        app.add_router(...)
        app.add_router(...)
        ...
        app.finish()
    """

    def __init__(
            self,
            apis: Dict[int, fastapi.FastAPI],
            *args,
            version_format: str = "/v{}",
            logger: Optional[logging.Logger] = None,
            absolute_minimal_version: int = 0,
            absolute_maximal_version: Optional[int] = None,
            **kwargs
    ):
        assert version_format.count("{}") == 1, "Version format string must contain '{}' once"
        super().__init__(*args, **kwargs)
        self._apis = apis
        self._version_format = version_format
        self._logger = logger or logging.getLogger(__name__)
        self._abs_min = absolute_minimal_version
        self._abs_max = absolute_maximal_version or max(apis.keys())
        self._finished = False

    def finish(self, versions_endpoint: bool = True):
        """
        Complete the registration of new routers and build the relevant API routes once

        :param versions_endpoint: switch to enable the special ``/versions`` endpoint
        """

        if self._finished:
            return

        for api_version in self._apis:
            prefix = self._version_format.format(api_version)
            api_tag = f"Version {api_version}"
            finish = getattr(self._apis[api_version], "finish", None)
            if finish and isinstance(finish, Callable):
                finish()
            self.mount(prefix, self._apis[api_version])

            @self.get(f"{prefix}/openapi.json", name="Get Specifications", tags=[api_tag])
            @self.get(f"{prefix}/docs", name="Use Swagger User Interface", tags=[api_tag])
            @self.get(f"{prefix}/redoc", name="Use ReDoc User Interface", tags=[api_tag])
            async def noop() -> None:
                pass

        if versions_endpoint:
            @self.get("/versions", response_model=schemas.Versions, tags=["Miscellaneous"])
            async def get_version_info():
                return schemas.Versions(
                    latest=max(self._apis.keys()),
                    versions=[
                        {"version": v, "prefix": self._version_format.format(v)}
                        for v in self._apis.keys()
                    ]
                )

        self._finished = True

    def add_router(self, router: fastapi.APIRouter, **kwargs):
        """
        Add the routes of the router to the set of sub-APIs which fulfill their requirements

        :param router: APIRouter carrying all routes that should be filtered and added
        :param kwargs: optional keyword arguments for the ``include_router`` method of the
            ``FastAPI`` instances which were supplied via the constructor's ``apis`` argument
        :raises TypeError: when there are problems with the annotated values of the endpoints
        """

        if self._finished:
            raise RuntimeError("Can't add new routers after the API has been finally built")

        for api_version in self._apis:
            filtered_routes = []
            for route in router.routes:
                if not isinstance(route, fastapi.routing.APIRoute):
                    self._logger.error(
                        f"Route {route!r} (type {type(route)!r}) is no 'APIRoute' instance! "
                        "Further operation might work properly, but is not guaranteed to."
                    )

                endpoint = getattr(route, "endpoint", None)
                if endpoint is None:
                    self._logger.error(f"Route {route!r} has no attribute 'endpoint'! Skipping.")
                    continue

                min_version = getattr(endpoint, MINIMAL_VERSION_ANNOTATION_NAME, self._abs_min)
                if not isinstance(min_version, int):
                    raise TypeError(f"Min version annotation {min_version!r} is no integer!")
                max_version = getattr(endpoint, MAXIMAL_VERSION_ANNOTATION_NAME, self._abs_max)
                if not isinstance(max_version, int):
                    raise TypeError(f"Max version annotation {max_version!r} is no integer!")

                explicit_versions = getattr(endpoint, VERSION_ANNOTATION_NAME, [])
                if not isinstance(explicit_versions, Iterable):
                    raise TypeError(f"Version annotation {explicit_versions!r} is not iterable!")
                if not all(map(lambda v: isinstance(v, int), explicit_versions)):
                    raise TypeError(f"Not all versions in {explicit_versions!r} are integers!")

                if not any([
                    hasattr(endpoint, VERSION_ANNOTATION_NAME),
                    hasattr(endpoint, MINIMAL_VERSION_ANNOTATION_NAME),
                    hasattr(endpoint, MAXIMAL_VERSION_ANNOTATION_NAME)
                ]):
                    self._logger.warning(
                        f"Route {route!r} has no supported annotated version! It will "
                        f"therefore only be supported on API version {max_version} by default."
                    )

                if min_version <= api_version <= max_version:
                    if not explicit_versions or api_version in explicit_versions:
                        filtered_routes.append(route)

            kwargs.pop("prefix", None)
            self._apis[api_version].include_router(
                fastapi.APIRouter(
                    prefix="",
                    default_response_class=router.default_response_class,
                    routes=filtered_routes,
                    on_startup=router.on_startup,
                    on_shutdown=router.on_shutdown,
                ),
                prefix="",
                **kwargs
            )
