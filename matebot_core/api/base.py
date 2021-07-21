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

    @classmethod
    async def handle(cls, request: Request, exc: HTTPException):
        return JSONResponse(status_code=304, headers=exc.headers, content={
            "code": 304,
            "message": "Resource not modified.",
            "detail": exc.detail,
            "request": request.url.path
        })


class PreconditionFailed(HTTPException):
    """
    TODO
    """

    @classmethod
    async def handle(cls, request: Request, exc: HTTPException):
        return JSONResponse(status_code=412, headers=exc.headers, content={
            "code": 412,
            "message": "Precondition failed.",
            "detail": exc.detail,
            "request": request.url.path
        })


class MissingImplementation(HTTPException):
    """
    Exception raised if a path operation doesn't implement a required feature to work

    This exception should be caught by a special handler
    that uses its class method `handle` to create a response.
    """

    def __init__(self, feature: str):
        super().__init__(status_code=501, detail=feature)

    @classmethod
    async def handle(cls, request: Request, exc: HTTPException):
        print(
            f"Feature '{exc.detail}' (required for '{request.method} "
            f"{request.url.path}') not implemented yet.",
            file=sys.stderr
        )

        return JSONResponse(status_code=501, content={
            "code": 501,
            "message": "Feature not implemented.",
            "detail": exc.detail,
            "request": request.url.path
        })
