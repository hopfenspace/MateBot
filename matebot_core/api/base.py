"""
MateBot REST API base library
"""

import time
import uuid
import random
import string
import logging
from typing import List, Optional, Union

import pydantic
from fastapi import HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.responses import JSONResponse

from .. import schemas


logger = logging.getLogger(__name__)

startup = time.time()
runtime_key = "".join([random.choice(string.hexdigits) for _ in range(32)]).lower()
runtime_uuid = uuid.UUID(runtime_key)

ModelType = Union[pydantic.BaseModel, List[pydantic.BaseModel]]


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
    async def handle(cls, request: Request, exc: HTTPException) -> Response:
        """
        Handle exceptions in a generic way to produce APIError models
        """

        hook_message = None
        if hasattr(exc, "hook") and callable(exc.hook):
            hook_message = await exc.hook(request)

        status_code = 500
        if hasattr(exc, "status_code"):
            status_code = exc.status_code
        elif isinstance(exc, pydantic.ValidationError):
            status_code = 422

        if not isinstance(exc, HTTPException):
            details = jsonable_encoder(exc)
            if len(details) == 0:
                details = jsonable_encoder({
                    "args": str(exc.args),
                    "cause": str(exc.__cause__),
                    "context": str(exc.__context__),
                    "str": str(exc)
                })

            logger.error(
                f"{type(exc).__name__}: {exc} @ '{request.method} "
                f"{request.url.path}' (details: {details})"
            )
            return JSONResponse(jsonable_encoder(schemas.APIError(
                status=status_code,
                request=request.url.path,
                repeat=False,
                message=exc.__class__.__name__,
                details=str(details)
            )), status_code=status_code)

        repeat = False
        if hasattr(exc, "repeat"):
            repeat = exc.repeat
        message = exc.__class__.__name__
        if hasattr(exc, "message"):
            if exc.message is not None:
                message = exc.message
        if hook_message is not None:
            message = hook_message

        logger.debug(
            f"{type(exc).__name__}: {message} @ '{request.method} "
            f"{request.url.path}' (details: {exc.detail}"
        )
        return JSONResponse(jsonable_encoder(schemas.APIError(
            status=status_code,
            request=request.url.path,
            repeat=repeat,
            message=message,
            details=exc.detail
        )), status_code=status_code, headers=exc.headers)


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


class NotFound(APIException):
    """
    Exception when a requested resource was not found in the system
    """

    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(
            status_code=404,
            detail=detail,
            repeat=False,
            message=f"{resource} was not found."
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
        logger.error(
            f"Feature '{self.detail}' (required for '{request.method} "
            f"{request.url.path}') not implemented yet."
        )
        return
