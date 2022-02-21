"""
MateBot router module for authentication
"""

import logging

from fastapi import APIRouter, Depends
from fastapi.security import OAuth2PasswordRequestFormStrict

from ..base import APIException
from ..dependency import MinimalRequestData
from .. import auth, versioning
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(tags=["Authentication"])


@router.post("/login", response_model=schemas.Token)
@versioning.versions(1)
async def login(
        data: OAuth2PasswordRequestFormStrict = Depends(),
        local: MinimalRequestData = Depends(MinimalRequestData)
):
    logger.debug(f"Login request using username {data.username!r}...")
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
