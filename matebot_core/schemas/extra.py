"""
MateBot extra schemas

This module contains the special schemas for updates and the status.
"""

import time
import datetime
from typing import List, Optional

import pydantic


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
    timezone: str = time.localtime().tm_zone
    localtime: datetime.datetime
    timestamp: pydantic.NonNegativeInt


class Callback(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    url: pydantic.stricturl(max_length=255, tld_required=False, allowed_schemes=_URL_SCHEMES)
    application_id: Optional[pydantic.NonNegativeInt]


class CallbackCreation(pydantic.BaseModel):
    url: pydantic.stricturl(max_length=255, tld_required=False, allowed_schemes=_URL_SCHEMES)
    application_id: Optional[pydantic.NonNegativeInt]
    shared_secret: Optional[pydantic.constr(max_length=255)]
