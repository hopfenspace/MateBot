"""
MateBot REST API base library
"""

import enum
import time
import uuid
import logging
import secrets
from typing import Any, Dict, List, Optional, Union

import pydantic
from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.openapi.utils import get_openapi
from fastapi.responses import JSONResponse

from .. import schemas


logger = logging.getLogger(__name__)

startup = time.time()
runtime_key = secrets.token_hex(16)
runtime_uuid = uuid.UUID(runtime_key)

ModelType = Union[pydantic.BaseModel, List[pydantic.BaseModel]]


@enum.unique
class Operations(enum.Enum):
    CREATE = "Creating"
    UPDATE = "Updating"
    PATCH = "Patching"
    DELETE = "Deleting"


class ReturnType(enum.Enum):
    NONE = enum.auto()
    MODEL = enum.auto()
    SCHEMA = enum.auto()


class APIWithoutValidationError(FastAPI):
    """
    FastAPI class that excludes 422 validation error responses in OpenAPI schema
    """

    def openapi(self) -> Dict[str, Any]:
        if not self.openapi_schema:
            self.openapi_schema = get_openapi(
                title=self.title,
                version=self.version,
                openapi_version=self.openapi_version,
                description=self.description,
                terms_of_service=self.terms_of_service,
                contact=self.contact,
                license_info=self.license_info,
                routes=self.routes,
                tags=self.openapi_tags,
                servers=self.servers,
            )
            for path, operations in self.openapi_schema["paths"].items():
                for method, metadata in operations.items():
                    metadata["responses"].pop("422", None)
        return self.openapi_schema


async def handle_request_validation_error(request: Request, exc: RequestValidationError):
    status_code = 400
    msgs = "\n".join(["\t" + error["msg"] for error in exc.errors()])
    message = f"Failed to process the request:\n{msgs}\nYou may want to file a bug report."

    return JSONResponse(jsonable_encoder(schemas.APIError(
        status=status_code,
        method=request.method,
        request=request.url.path,
        repeat=False,
        message=message,
        details=str(exc.errors())
    )), status_code=status_code)


class APIException(HTTPException):
    """
    Base class for any kind of generic API exception
    """

    def __init__(
            self,
            status_code: int,
            detail: str,
            repeat: bool = False,
            message: Optional[str] = None,
            headers: Optional[Dict[str, Any]] = None
    ):
        super().__init__(status_code=status_code, detail=detail, headers=headers)
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

        if not isinstance(exc, HTTPException):
            details = jsonable_encoder(exc)
            if len(details) == 0:
                details = jsonable_encoder({
                    "args": str(exc.args),
                    "cause": str(exc.__cause__),
                    "context": str(exc.__context__),
                    "str": str(exc)
                })
            if "str" not in details:
                details["str"] = str(exc)

            if isinstance(exc, pydantic.ValidationError) and not isinstance(exc, RequestValidationError):
                status_code = 500
                details = "Please file a bug report. Thanks."

            logger.exception(
                f"{type(exc).__name__}: {exc} @ '{request.method} "
                f"{request.url.path}' (details: {details})"
            )
            return JSONResponse(jsonable_encoder(schemas.APIError(
                status=status_code,
                method=request.method,
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
            f"{request.url.path}' (details: {exc.detail})"
        )
        return JSONResponse(jsonable_encoder(schemas.APIError(
            status=status_code,
            method=request.method,
            request=request.url.path,
            repeat=repeat,
            message=message,
            details=str(exc.detail)
        )), status_code=status_code, headers=exc.headers)


class BadRequest(APIException):
    """
    Exception when the user probably messed something up

    The `message` field must be user-friendly and not too informative!
    """

    def __init__(self, message: str, detail: Optional[str] = None):
        super().__init__(
            status_code=400,
            detail=detail,
            repeat=True,
            message=message
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
            message=f"{str(resource)!r} was not found."
        )


class Conflict(APIException):
    """
    Exception for invalid states, concurrent manipulations or other data clashes
    """

    def __init__(self, message: str, detail: Optional[str] = None, repeat: bool = False):
        super().__init__(
            status_code=409,
            detail=detail,
            repeat=repeat,
            message=message
        )


class ForbiddenChange(APIException):
    """
    Exception when a resource was requested to be changed which is forbidden
    """

    def __init__(self, resource: str, detail: Optional[str] = None):
        super().__init__(
            status_code=409,
            detail=detail,
            repeat=False,
            message=f"Resource '{resource}' may not be modified."
        )


class InternalServerException(APIException):
    """
    Exception for problems within the server implementation
    """

    def __init__(self, message: str, detail: Optional[str] = None, repeat: bool = False):
        super().__init__(
            status_code=500,
            detail=detail,
            repeat=repeat,
            message=message
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
