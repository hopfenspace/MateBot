"""
MateBot REST API base library
"""

import sys
import enum

from fastapi import HTTPException, Request
from fastapi.responses import JSONResponse


class RequestMethodType(enum.Enum):
    GET = enum.auto()
    POST = enum.auto()
    PUT = enum.auto()
    DELETE = enum.auto()


class NotModified(HTTPException):
    """
    TODO
    """


class PreconditionFailed(HTTPException):
    """
    TODO
    """


class MissingImplementation(HTTPException):
    """
    TODO
    """

    def __init__(self, feature: str):
        super().__init__(status_code=501, detail=feature)

    @staticmethod
    async def handle(request: Request, exc: HTTPException):
        print(f"Feature {exc.detail} by {request.url.path} not implemented yet.", file=sys.stderr)
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": exc.detail,
            "request": request.url.path
        })
