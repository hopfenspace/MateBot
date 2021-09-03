"""
MateBot API library to provide multiple versions of the API endpoints
"""

import logging
from typing import Callable, Dict, List, Optional

import fastapi

from .. import schemas


VERSION_ANNOTATION_NAME = "_api_versions"
MINIMAL_VERSION_ANNOTATION_NAME = "_minimal_api_version"


def version(version_annotation: int) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        annotated_versions = getattr(func, VERSION_ANNOTATION_NAME, [])
        annotated_versions.append(version_annotation)
        setattr(func, VERSION_ANNOTATION_NAME, annotated_versions)
        return func

    return decorator


def versions(version_annotations: List[int]) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        assert not hasattr(func, VERSION_ANNOTATION_NAME), "'versions' can't be used twice"
        setattr(func, VERSION_ANNOTATION_NAME, version_annotations)
        return func

    return decorator


def min_version(version_annotation: int) -> Callable[[Callable], Callable]:
    def decorator(func: Callable) -> Callable:
        setattr(func, MINIMAL_VERSION_ANNOTATION_NAME, version_annotation)
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

        @self.get("/latest", response_model=schemas.LatestVersion, tags=["Miscellaneous"])
        async def get_latest_api_version():
            return schemas.LatestVersion(
                version=max(self._apis.keys()),
                prefix=self._version_format.format(max(self._apis.keys()))
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
                if not isinstance(explicit_versions, list):
                    self._logger.error(f"Version annotation {explicit_versions!r} is no list!")
                    continue
                if not all(map(lambda v: isinstance(v, int), explicit_versions)):
                    self._logger.error(f"Not all versions in {explicit_versions!r} are integers!")
                    continue

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
