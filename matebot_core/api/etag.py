"""
ETag helper library for the core REST API
"""

import enum
import hashlib
import logging
import collections
from typing import Any, Optional

try:
    import ujson as json
except ImportError:
    import json

import pydantic
from fastapi import Request, Response
from fastapi.encoders import jsonable_encoder

from . import base


logger = logging.getLogger(__name__)


class HeaderFieldType(enum.Enum):
    ABSENT = None
    IF_MATCH = "If-Match"
    IF_NONE_MATCH = "If-None-Match"


class ETag:
    """
    Helper class providing methods to create and compare ETags and related headers
    """

    def __init__(self, request: Request):
        self.request = request
        self.match = request.headers.get("If-Match")
        self.none_match = request.headers.get("If-None-Match")

    def add_header(self, response: Response, model: base.ModelType):
        """
        Add the ETag header field of the model to the response

        :param response: Response object of the handled request
        :param model: generated model of the completely finished request
        """

        tag = self.make_etag(model)
        if tag is not None:
            response.headers.append("ETag", tag)

    def compare(self, current_model: Optional[base.ModelType] = None) -> bool:
        """
        Calculate and compare the ETag of the given model with the known client ETag

        This method raises appropriate exceptions to interrupt further object
        processing. In the following, setting the specified header field "correctly"
        means that the value in the header field matches the current state of
        the model. For GET requests, this allows to use the client's cached
        version. For modifying requests, this allows to detect mid-air collisions.

        :param current_model: any subclass of a base model or list thereof
        :return: ``True`` if everything went smoothly
        :raises NotModified: if the user agent already has the most recent version of a resource
        :raises PreconditionFailed: if any of the preconditions were not met
        """

        verified = False
        model_tag = self.make_etag(current_model)

        precondition_failed = base.PreconditionFailed(
            self.request.url.path,
            f"Conditional request not matching current model entity tag: {model_tag!r}"
        )

        def evaluate_match(header_value: str) -> bool:
            if header_value.strip() == "*":
                return model_tag is not None
            for tag in map(str.strip, header_value.split(",")):
                if tag != "" and not tag.startswith("W/") and tag.replace('"', '') == model_tag:
                    return True
            return False

        def evaluate_none_match(header_value: str) -> bool:
            if header_value.strip() == "*":
                return model_tag is None
            # TODO: the weak comparison algorithm should be used here (RFC 7232, 3.2) instead!
            for tag in map(str.strip, header_value.split(",")):
                if tag != "" and not tag.startswith("W/") and tag.replace('"', '') == model_tag:
                    return False
            return True

        # Step 1: evaluate the `If-Match` header precondition
        if self.match is not None and self.match != "":
            if not evaluate_match(self.match):
                raise precondition_failed
            if self.request.method == "GET":
                raise base.NotModified(self.request.url.path)
            verified = True

        # Step 2: evaluate the `If-None-Match` header precondition
        if self.none_match is not None and self.none_match != "":
            if not evaluate_none_match(self.none_match):
                if self.request.method == "GET":
                    raise base.NotModified(self.request.url.path)
                raise precondition_failed
            verified = True

        # Step 3: abort further operation if the preconditions were not met
        if self.request.method not in ("GET", "POST") and not verified:
            raise precondition_failed

        return True

    @staticmethod
    def make_etag(obj: Any) -> Optional[str]:
        """
        Create a static, weak and unambiguous ETag value based on a given object

        The method might return None in case the generation of the ETag failed.

        :param obj: any object that can be JSON-serialized
        :return: optional ETag value as a string
        """

        if obj is None:
            return

        weak = False
        if isinstance(obj, pydantic.BaseModel):
            representation = obj.dict()
        elif isinstance(obj, collections.Sequence):
            if any(map(lambda x: not isinstance(x, pydantic.BaseModel), obj)):
                logger.warning(f"Not all elements of the sequence of length {len(obj)} are models")
                representation = jsonable_encoder(obj)
                weak = True
            else:
                representation = [e.dict() for e in obj]
        else:
            logger.warning(f"Object {obj!r} ({type(object)}) is no valid model")
            representation = jsonable_encoder(obj)
            weak = True

        if representation is None or weak and representation == {}:
            logger.error(f"Could not generate ETag token for {obj!r}")
            return

        cls = type(obj).__name__
        dump = json.dumps(representation, allow_nan=False)
        content = cls + dump + base.runtime_key
        return f'"{hashlib.sha3_256(content.encode("UTF-8")).hexdigest()}"'
