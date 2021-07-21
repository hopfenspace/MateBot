"""
MateBot REST API base library
"""

import sys
import enum
import time
import uuid
import random
import string
from typing import Optional

from fastapi import HTTPException, Request
from fastapi.encoders import jsonable_encoder

from .. import schemas


startup = time.time()
runtime_key = "".join([random.choice(string.hexdigits) for _ in range(32)]).lower()
runtime_uuid = uuid.UUID(runtime_key)


class RequestMethodType(enum.Enum):
    GET = enum.auto()
    POST = enum.auto()
    PUT = enum.auto()
    DELETE = enum.auto()


class APIException(HTTPException):
    """
    Base class for any kind of generic API exception
    """

    def __init__(
            self,
            status_code: int,
            detail: str,
            repeat: bool = False,
            message: Optional[str] = None
    ):
        super().__init__(status_code=status_code, detail=detail)
        self.repeat = repeat
        self.message = message

    async def hook(self, request: Request) -> Optional[str]:
        """
        Hook into exception handling to do extra steps

        This method was designed to be overwritten in a subclass.

        :param request: the incoming request handled by this class
        :return: a message that optionally overwrites the stored message
        """

        pass

    @classmethod
    async def handle(cls, request: Request, exc: HTTPException) -> schemas.APIError:
        """
        Handle exceptions in a generic way to produce APIError models
        """

        hook_message = None
        if hasattr(exc, "hook") and callable(exc.hook):
            hook_message = await exc.hook(request)

        if not isinstance(exc, HTTPException):
            return schemas.APIError(
                status=500,
                request=request.url.path,
                repeat=False,
                message=exc.__class__.__name__,
                details=str(jsonable_encoder(exc))
            )

        repeat = False
        if hasattr(exc, "repeat"):
            repeat = exc.repeat
        message = exc.__class__.__name__
        if hasattr(exc, "message"):
            if exc.message is not None:
                message = exc.message
        if hook_message is not None:
            message = hook_message
        return schemas.APIError(
            status=exc.status_code,
            request=request.url.path,
            repeat=repeat,
            message=message,
            details=exc.detail
        )


class NotModified(APIException):
    """
    Exception when a requested resource hasn't changed since last request
    """

    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(
            status_code=304,
            detail=detail,
            repeat=True,
            message=f"Resource '{str(resource)}' has not been modified."
        )


class PreconditionFailed(APIException):
    """
    Exception when the precondition of a conditional request failed
    """

    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(
            status_code=412,
            detail=detail,
            repeat=False,
            message=f"Precondition failed for resource '{str(resource)}'."
        )


class MissingImplementation(APIException):
    """
    Exception raised if a path operation doesn't implement a required feature to work

    This exception should be caught by a special handler
    that uses its class method `handle` to create a response.
    """

    def __init__(self, feature: str):
        super().__init__(
            status_code=501,
            detail=feature,
            repeat=False,
            message=f"Feature '{feature}' not implemented yet. Stay tuned."
        )

    async def hook(self, request: Request) -> Optional[str]:
        print(
            f"Feature '{self.detail}' (required for '{request.method} "
            f"{request.url.path}') not implemented yet.",
            file=sys.stderr
        )
        return
