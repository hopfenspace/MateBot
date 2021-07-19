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


async def handle_cache_hit(request: Request, exc: NotModified):
    return Response("", 304, headers=exc.headers)


async def handle_failed_precondition(request: Request, exc: PreconditionFailed):
    return Response("", 412, headers=exc.headers)
