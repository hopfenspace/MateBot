"""
MateBot extra schemas

This module contains the special schemas for updates and the status.
"""

import sys
import time
import datetime
from typing import List, Optional

import pydantic

from .bases import BaseModel


_URL_SCHEMES = {"http", "https"}


class Versions(pydantic.BaseModel):
    class Version(pydantic.BaseModel):
        version: pydantic.PositiveInt
        prefix: pydantic.constr(min_length=2)

    latest: pydantic.PositiveInt
    versions: List[Version]


class VersionInfo(pydantic.BaseModel):
    major: pydantic.NonNegativeInt
    minor: pydantic.NonNegativeInt
    micro: pydantic.NonNegativeInt


class Status(pydantic.BaseModel):
    startup: pydantic.NonNegativeInt = int(datetime.datetime.now().timestamp())
    api_version: pydantic.PositiveInt
    project_version: VersionInfo
    python_version: VersionInfo = VersionInfo(
        major=sys.version_info.major,
        minor=sys.version_info.minor,
        micro=sys.version_info.micro
    )
    timezone: str = time.localtime().tm_zone
    localtime: datetime.datetime
    timestamp: pydantic.NonNegativeInt


class Callback(BaseModel):
    id: pydantic.NonNegativeInt
    base: pydantic.stricturl(max_length=255, tld_required=False, allowed_schemes=_URL_SCHEMES)
    app: Optional[pydantic.NonNegativeInt]
    username: Optional[pydantic.constr(max_length=255)]
    password: Optional[pydantic.constr(max_length=255)]

    __allowed_updates__ = ["base", "username", "password"]


class CallbackCreation(BaseModel):
    base: pydantic.stricturl(max_length=255, tld_required=False, allowed_schemes=_URL_SCHEMES)
    app: Optional[pydantic.NonNegativeInt]
    username: Optional[pydantic.constr(max_length=255)]
    password: Optional[pydantic.constr(max_length=255)]
