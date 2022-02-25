"""
MateBot router module for authentication
"""

import logging

from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestFormStrict

from ._router import router
from ..base import APIException
from ..dependency import MinimalRequestData
from .. import auth, versioning
from ... import schemas


logger = logging.getLogger(__name__)


@router.post("/login", tags=["Authentication"], response_model=schemas.Token)
@versioning.versions(1)
async def login(
        data: OAuth2PasswordRequestFormStrict = Depends(),
        local: MinimalRequestData = Depends(MinimalRequestData)
):
    """
    Login using username and password via the OAuth Password Flow

    Note that this endpoint is currently the only API endpoint that
    uses URL-encoded form data instead of JSON bodies, since this
    is enforced by the OAuth standard for the Password Flow.

    See RFC 6749, section 1.3.3, for more details.
    """

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
