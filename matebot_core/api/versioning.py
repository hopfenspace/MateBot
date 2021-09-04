"""
MateBot API library to provide multiple versions of the API endpoints
"""

import logging
from typing import Callable, Dict, Iterable, Optional

import fastapi

from .. import schemas


VERSION_ANNOTATION_NAME = "_api_versions"
MINIMAL_VERSION_ANNOTATION_NAME = "_minimal_api_version"


def versions(*annotations: int, minimal: Optional[int] = None) -> Callable[[Callable], Callable]:
    if not all(map(lambda x: isinstance(x, int), annotations)):
        raise TypeError(f"Not all annotations are integers: {annotations!r}")
    if minimal and not isinstance(minimal, int):
        raise TypeError(f"Expected int, got {type(minimal)!r}")
    if annotations and minimal:
        raise RuntimeError("Can't use explicit versions and minimal versions at the same time")

    def decorator(func: Callable) -> Callable:
        assert not hasattr(func, VERSION_ANNOTATION_NAME), "'versions' can't be used twice"
        assert not hasattr(func, MINIMAL_VERSION_ANNOTATION_NAME), "'versions' can't be used twice"
        if annotations:
            setattr(func, VERSION_ANNOTATION_NAME, annotations)
        if minimal:
            setattr(func, MINIMAL_VERSION_ANNOTATION_NAME, minimal)
        return func

    return decorator


class VersionedFastAPI(fastapi.FastAPI):
    def __init__(
            self,
            apis: Dict[int, fastapi.FastAPI],
            *args,
            version_format: str = "/v{}",
            logger: Optional[logging.Logger] = None,
            **kwargs
    ):
        assert version_format.count("{}") == 1, "Version format string must contain '{}' once"
        super().__init__(*args, **kwargs)
        self._apis = apis
        self._version_format = version_format
        self._logger = logger or logging.getLogger(__name__)

    def finish(self):
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

        @self.get("/versions", response_model=schemas.Versions, tags=["Miscellaneous"])
        async def get_version_info():
            return schemas.Versions(
                latest=max(self._apis.keys()),
                versions=[{"version": v, "prefix": self._version_format.format(v)} for v in self._apis.keys()]
            )

    def add_router(self, router: fastapi.APIRouter, **kwargs):
        max_version = max(self._apis.keys())
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

                has_min_tag = hasattr(endpoint, MINIMAL_VERSION_ANNOTATION_NAME)
                min_tag = getattr(endpoint, MINIMAL_VERSION_ANNOTATION_NAME, max_version)
                if not isinstance(min_tag, int):
                    self._logger.error(f"Min version annotation {min_tag!r} is no integer!")
                    continue

                has_explicit_versions = hasattr(endpoint, VERSION_ANNOTATION_NAME)
                explicit_versions = getattr(endpoint, VERSION_ANNOTATION_NAME, [])
                if not isinstance(explicit_versions, Iterable):
                    self._logger.error(f"Version annotation {explicit_versions!r} is no list!")
                    continue
                if not all(map(lambda v: isinstance(v, int), explicit_versions)):
                    self._logger.error(f"Not all versions in {explicit_versions!r} are integers!")
                    continue

                if not has_min_tag and not has_explicit_versions:
                    self._logger.warning(
                        f"Route {route!r} has no supported annotated version! It will "
                        f"therefore be only supported on API version {max_version} by default."
                    )

                if (
                    (has_min_tag and not has_explicit_versions and min_tag <= api_version)
                    or
                    (not has_min_tag and has_explicit_versions and api_version in explicit_versions)
                    or
                    (not has_min_tag and not has_explicit_versions and api_version == max_version)
                ):
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
