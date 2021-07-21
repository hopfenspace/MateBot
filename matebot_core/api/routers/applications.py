"""
MateBot router module for /applications requests
"""

import logging
from typing import List

from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/applications",
    tags=["Applications"]
)


@router.get(
    "",
    response_model=List[schemas.Application],
    description="Return a list of all known applications with their respective ID (=`app_id`)."
)
def get_all_applications(local: LocalRequestData = Depends(LocalRequestData)):
    raise MissingImplementation("get_all_applications")


@router.post(
    "",
    response_model=schemas.Application,
    responses={409: {}},
    description="Add a new application and create a new ID for it. The UUID `auth_token` "
                "is used as a special form of API key to enforce proper authentication. "
                "The required alias for the `special_user` is used to create a proper "
                "binding to the \"banking user\" for the newly created application. "
                "A 409 error will be returned if the application already exists."
)
def add_new_application(
        application: schemas.IncomingApplication,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("add_new_application")
