"""
MateBot router module for various different requests without specialized purpose
"""

import logging
import datetime

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestFormStrict

from ..base import APIException
from ..dependency import LocalRequestData, MinimalRequestData
from .. import auth, versioning
from ...schemas import config
from ... import schemas, __version__


logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Generic"]
)


@router.post("/login", response_model=schemas.Token)
@versioning.versions(1)
async def login(
        data: OAuth2PasswordRequestFormStrict = Depends(),
        local: MinimalRequestData = Depends(MinimalRequestData)
):
    if not await auth.check_app_credentials(data.username, data.password, local.session):
        raise APIException(
            status_code=401,
            detail=f"username={data.username!r}, password=?",
            message="Invalid credentials"
        )

    return {
        "access_token": auth.create_access_token(data.username),
        "token_type": "bearer"
    }


@router.get("/status", response_model=schemas.Status)
@versioning.versions(1)
async def get_status():
    """
    Return some information about the current status of the server, the database and whatsoever.
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


@router.get("/settings", response_model=config.GeneralConfig)
@versioning.versions(minimal=1)
async def get_settings(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return the important MateBot core settings which directly affect the handling of requests.
    """

    return local.config.general
