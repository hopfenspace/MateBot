"""
ETag helper library for the core REST API
"""

import enum
import json
import hashlib
from typing import Union, List

import pydantic
from fastapi import Request, Response



from .base import NotModified, PreconditionFailed


class HeaderFieldType(enum.Enum):
    ABSENT = None
    IF_MATCH = "If-Match"
    IF_NONE_MATCH = "If-None-Match"


async def handle_cache_hit(request: Request, exc: NotModified):
    return Response("", 304, headers=exc.headers)


async def handle_failed_precondition(request: Request, exc: PreconditionFailed):
    return Response("", 412, headers=exc.headers)


class Entity:
    """
    TODO
    """

    def __init__(self, request: Request):
        self.request = request

        if request.headers.get("If-Match") is not None:
            self.client_tag = request.headers.get("If-Match")
            self.client_tag_type = HeaderFieldType.IF_MATCH
        elif request.headers.get("If-None-Match") is not None:
            self.client_tag = request.headers.get("If-None-Match")
            self.client_tag_type = HeaderFieldType.IF_NONE_MATCH
        else:
            self.client_tag = None
            self.client_tag_type = HeaderFieldType.ABSENT

    def compare(self, model: Union[pydantic.BaseModel, List[pydantic.BaseModel]]) -> bool:
        """
        Calculate and compare the ETag of the given model with the known client ETag

        This method raises appropriate exceptions to interrupt further object
        processing. In the following, setting the specified header field "correctly"
        means that the value in the header field matches the current state of
        the model. For GET requests, this allows to use the client's cached
        version. For modifying requests, this allows to detect mid-air collisions.

        :param model: any subclass of a base model or list thereof
        :return: ``True`` if everything went smoothly
        :raises NotModified: if the ``If-None-Match`` header for GET requests was set correctly
        :raises PreconditionFailed: if the ``If-Match`` header for other requests was set correctly
        """

        # TODO: implement this method!
        return False

    @staticmethod
    def make_etag(json_object: Union[list, dict]) -> str:
        """
        Create a static, weak and unambiguous ETag value based on a given JSON object

        :param json_object: any list or dict that can be JSON-serialized
        :return: weak ETag value as a string
        """

        return f'W/"{hashlib.sha3_256(json.dumps(json_object).encode("UTF-8")).hexdigest()}"'
