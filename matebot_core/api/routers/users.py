"""
MateBot router module for /users requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get(
    "",
    response_model=List[schemas.User],
    description="Return a list of all internal user models with their aliases."
)
def get_all_users(local: LocalRequestData = Depends(LocalRequestData)):
    all_users = [u.schema for u in local.session.query(models.User).all()]
    local.entity.compare(all_users)
    return local.attach_headers(all_users)


@router.post(
    "",
    response_model=schemas.User,
    description="Create a new \"empty\" user account with zero balance."
)
def create_new_user(
        user: schemas.IncomingUser,
        local: LocalRequestData = Depends(LocalRequestData)
):
    local.entity.compare(None)
    values = user.dict()
    values["voucher_id"] = values["voucher"]
    del values["voucher"]
    model = models.User(**values)
    logger.info(f"Adding new user {model.name!r} (external: {model.external!r})...")
    local.session.add(model)
    local.session.commit()
    return local.attach_headers(model.schema)


@router.put(
    "",
    response_model=schemas.User,
    responses={404: {}, 409: {}},
    description="Update an existing user model identified by the `user_id`. A 404 error "
                "will be returned if the `user_id` is not known. A 409 error will be "
                "returned when some of the following fields have been changed compared "
                "to the internal user state: `balance`, `created`, `accessed`."
)
def update_existing_user(
        user: schemas.User,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("update_existing_user")


@router.get(
    "/{user_id}",
    response_model=schemas.User,
    description="Return the internal model of the user specified by its user ID."
)
def get_user_by_id(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_user_by_id")
