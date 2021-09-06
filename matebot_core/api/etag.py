"""
ETag helper library for the core REST API
"""

import uuid
import hashlib
import logging
import collections.abc
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

        for field in ["If-None-Match", "If-Modified-Since", "If-Unmodified-Since", "If-Range"]:
            if request.headers.get(field):
                logger.warning(f"'{field}' header not supported or not fully implemented.")
                logger.debug(f"Field value: {request.headers.get(field)!r}")

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

        model_tag = self.make_etag(current_model, self.model_name)

        precondition_failed = base.PreconditionFailed(
            self.request.url.path,
            f"Conditional request not matching current model entity tag: {model_tag}"
        )

        match = self.request.headers.get("If-Match")
        if len(self.request.headers.getlist("If-Match")) > 1:
            logger.warning(f"More than one 'If-Match' header: {self.request.headers.items()}")

        if match is not None and match != "":
            if match.strip() == "*":
                if model_tag is None:
                    raise precondition_failed
                logger.warning(
                    f"Request for '{self.request.method} {self.request.url.path}' "
                    f"had 'If-Match' header value '*' for current model {model_tag}."
                )
                return True

            for tag in map(str.strip, match.split(",")):
                if tag.startswith('"'):
                    tag = tag[1:]
                if tag.endswith('"'):
                    tag = tag[:-1]
                if tag != "" and not tag.startswith("W/") and tag == model_tag:
                    if self.request.method == "GET":
                        raise base.NotModified(self.request.url.path)
                    return True

        if self.request.method not in ("GET", "POST"):
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
        elif isinstance(obj, collections.abc.Sequence):
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
