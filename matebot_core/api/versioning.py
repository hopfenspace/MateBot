"""
MateBot API library to provide multiple versions of the API endpoints
"""

from typing import Callable, Dict, List, Optional

from fastapi import FastAPI, APIRouter


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


class VersionedFastAPI(FastAPI):
    def __init__(self, versions: Dict[int, FastAPI], *args, version_fmt: str = "/v{}", **kwargs):
        super().__init__(*args, **kwargs)
        self._versions = versions
        self._version_fmt = version_fmt

    def finish(self):
        for k in self._versions:
            finish = getattr(self._versions[k], "finish", None)
            if finish and isinstance(finish, Callable):
                finish()
            self.mount(self._version_fmt.format(k), self._versions[k])

    def add_router(self, router: APIRouter, **kwargs):
        for k in self._versions:
            prefix = self._version_fmt.format(k) + kwargs.pop("prefix", "")
            self._versions[k].include_router(router, prefix=prefix, **kwargs)

