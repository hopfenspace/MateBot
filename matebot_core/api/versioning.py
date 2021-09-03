"""
MateBot API library to provide multiple versions of the API endpoints
"""

from fastapi import FastAPI, APIRouter


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

    def add_router(self, router: routing.APIRouter, **kwargs):
        for k in self._versions:
            self._versions[k].include_router(router, prefix=self._version_fmt.format(k), **kwargs)

