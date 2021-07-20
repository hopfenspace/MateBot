"""
MateBot REST API base library
"""

import enum

from fastapi import HTTPException
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


def _return_not_implemented_response(feature: str):
    return JSONResponse(status_code=501, content={
        "message": "Feature not implemented.",
        "feature": feature
    })
