"""
MateBot router module generic functionalities
"""

import datetime

from fastapi import Depends

from ._router import router
from ..dependency import LocalRequestData
from .. import versioning
from ...schemas import config
from ... import schemas, __version__


@router.get("/settings", tags=["Generic"], response_model=config.GeneralConfig)
@versioning.versions(minimal=1)
async def get_settings(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return the important MateBot core settings which directly affect the handling of requests
    """

    return local.config.general


@router.get("/status", tags=["Generic"], response_model=schemas.Status)
@versioning.versions(1)
async def get_status(_: LocalRequestData = Depends(LocalRequestData)):
    """
    Return some information about the current status of the server, the database and whatsoever
    """

    project_version_list = __version__.split(".") + [0, 0]
    project_version = schemas.VersionInfo(
        major=project_version_list[0],
        minor=project_version_list[1],
        micro=project_version_list[2]
    )

    return schemas.Status(
        api_version=1,
        project_version=project_version,
        localtime=datetime.datetime.now(),
        timestamp=datetime.datetime.now().timestamp()
    )
