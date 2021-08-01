"""
MateBot router module for /users requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from .. import helpers
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
    return helpers.get_all_of_model(models.User, local)


@router.post(
    "",
    response_model=schemas.User,
    description="Create a new \"empty\" user account with zero balance."
)
def create_new_user(
        user: schemas.UserCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    values = user.dict()
    values["voucher_id"] = values["voucher"]
    del values["voucher"]
    model = models.User(**values)
    return helpers.create_new_of_model(model, local, logger, "/users/{}", True)


@router.put(
    "",
    response_model=schemas.User,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}},
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


@router.delete(
    "",
    status_code=204,
    responses={409: {"model": schemas.APIError}},
    description="Delete an existing user model. A 409 error will be returned if "
                "the balance of the user is not zero or if there are any open "
                "refund requests or communisms that were either created by that "
                "user or which this user participates in. This operation will "
                "also delete any user aliases, but no user history or transactions. "
                "This operation requires a valid header for conditional requests."
)
def delete_existing_user(
        user: schemas.User,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("delete_existing_user")


@router.get(
    "/{user_id}",
    response_model=schemas.User,
    responses={404: {"model": schemas.APIError}},
    description="Return the internal model of the user specified by its user ID. "
                "A 404 error will be returned in case the user ID is unknown."
)
def get_user_by_id(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    return helpers.get_one_of_model(user_id, models.User, local)


@router.delete(
    "/{user_id}",
    status_code=204,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}},
    description="Delete an existing user model identified by its user ID. A 409 "
                "error will be returned if there are any open refund requests or "
                "communisms that were either created by that user or which this user "
                "participates in. Note that a balance other than zero is acceptable "
                "in this endpoint, as long as there's some other user vouching for "
                "the user in question. The voucher will either receive the remaining "
                "money or has to pay remaining bills. This operation will also "
                "delete any user aliases, but no user history or transactions. "
                "A 404 error will be returned in case the user ID is unknown."
)
def delete_existing_user_by_id(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("delete_existing_user_by_id")
