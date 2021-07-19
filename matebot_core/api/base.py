"""
MateBot REST API base library
"""

import enum

from fastapi import HTTPException


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
