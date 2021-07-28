"""
ETag helper library for the core REST API
"""

import uuid
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


class ETag:
    """
    Helper class providing methods to create and compare ETags and related headers
    """

    request: Request
    model_name: Optional[str]

    def __init__(self, request: Request):
        self.request = request
        self.model_name = None

        if request.headers.get("If-None-Match"):
            logger.warning("'If-None-Match' header not fully supported yet.")
            logger.debug(f"Field value{request.headers.get('If-None-Match')!r}")

    def add_header(self, response: Response, model: base.ModelType) -> bool:
        """
        Add the ETag header field of the model to the response

        :param response: Response object of the handled request
        :param model: generated model of the completely finished request
        :return: whether the ETag header has been set on the response
        """

        tag = self.make_etag(model, self.model_name)
        if tag is not None:
            if not tag.startswith('"'):
                tag = '"' + tag
            if not tag.endswith('"'):
                tag += '"'
            response.headers.append("ETag", tag)
        return tag is not None

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
        model_tag = self.make_etag(current_model, self.model_name)

        precondition_failed = base.PreconditionFailed(
            self.request.url.path,
            f"Conditional request not matching current model entity tag: {model_tag}"
        )

        def evaluate_match(header_value: str) -> bool:
            if header_value.strip() == "*":
                return model_tag is not None
            for tag in map(str.strip, header_value.split(",")):
                if tag.startswith('"'):
                    tag = tag[1:]
                if tag.endswith('"'):
                    tag = tag[:-1]
                if tag != "" and not tag.startswith("W/") and tag == model_tag:
                    return True
            return False

        def evaluate_none_match(header_value: str) -> bool:
            if header_value.strip() == "*":
                return model_tag is None
            # TODO: the weak comparison algorithm should be used here (RFC 7232, 3.2) instead!
            for tag in map(str.strip, header_value.split(",")):
                if tag.startswith('"'):
                    tag = tag[1:]
                if tag.endswith('"'):
                    tag = tag[:-1]
                if tag != "" and not tag.startswith("W/") and tag == model_tag:
                    return False
            return True

        # Step 1: evaluate the `If-Match` header precondition
        match = self.request.headers.get("If-Match")
        if match is not None and match != "":
            if not evaluate_match(match):
                raise precondition_failed
            if self.request.method == "GET":
                raise base.NotModified(self.request.url.path)
            verified = True

        # Step 2: evaluate the `If-None-Match` header precondition
        none_match = self.request.headers.get("If-None-Match")
        if none_match is not None and none_match != "":
            if not evaluate_none_match(none_match):
                if self.request.method == "GET":
                    raise base.NotModified(self.request.url.path)
                raise precondition_failed
            verified = True

        # Step 3: abort further operation if the preconditions were not met
        if self.request.method not in ("GET", "POST") and not verified:
            raise precondition_failed

        return True

    @staticmethod
    def make_etag(obj: Any, name: Optional[str] = None) -> Optional[str]:
        """
        Create a static and unambiguous ETag value based on a given object

        The method might return None in case the generation of the ETag failed.

        :param obj: any object that can be JSON-serialized
        :param name: optional string describing the object type (e.g. class name)
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
        content = cls + dump + base.runtime_key + (name or "")
        return str(uuid.UUID(hashlib.md5(content.encode("UTF-8")).hexdigest()))
