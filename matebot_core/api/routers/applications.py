"""
MateBot router module for /applications requests
"""

import logging
import secrets
from typing import List

from fastapi import APIRouter, Depends

from ..dependency import LocalRequestData
from .. import auth, helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=List[schemas.Application]
)
@versioning.versions(minimal=1)
async def get_all_applications(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known applications.
    """

    return await helpers.get_all_of_model(models.Application, local)


@router.get(
    "/{application_id}",
    response_model=schemas.Application,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_application_by_id(
        application_id: int,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the application model specified by its application ID.

    A 404 error will be returned in case the ID is not found.
    """

    return await helpers.get_one_of_model(application_id, models.Application, local)
