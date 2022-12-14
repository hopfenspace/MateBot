"""
MateBot router module generic functionalities
"""

import pydantic
from fastapi import Depends

from ._router import router
from ..dependency import LocalRequestData, MinimalRequestData
from .. import versioning
from ...schemas import config


@router.get("/health", tags=["Generic"], response_model=pydantic.BaseModel)
@versioning.versions(1)
async def verify_running_backend(_: MinimalRequestData = Depends(MinimalRequestData)):
    """
    Return 200 OK with an empty object as body to only verify that the service and the middlewares work
    """

    return {}


@router.get("/settings", tags=["Generic"], response_model=config.GeneralConfig)
@versioning.versions(minimal=1)
async def get_settings(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return the important MateBot core settings which directly affect the handling of requests
    """

    return local.config.general
