"""
MateBot router module for /communisms requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from ... import schemas
from ...persistence import models


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/communisms",
    tags=["Communisms"]
)


@router.get(
    "",
    response_model=List[schemas.Communism],
    description="Return a list of all communisms in the system."
)
def get_all_communisms(local: LocalRequestData = Depends(LocalRequestData)):
    all_communisms = [c.schema for c in local.session.query(models.Communism).all()]
    local.entity.compare(all_communisms)
    return local.attach_headers(all_communisms)


@router.post(
    "",
    response_model=schemas.Communism,
    responses={404: {}},
    description="Create a new communism based on the specified data. A 404 error will be "
                "returned if the user ID of the creator of that communism is unknown."
)
def create_new_communism(
        communism: schemas.IncomingCommunism,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("create_new_communism")


@router.put(
    "",
    response_model=schemas.Communism,
    responses={404: {}, 409: {}},
    description="Update an existing communism based on the specified data. A 404 error "
                "will be returned if the communism ID was not found. A 409 error will "
                "be returned if any of the following fields was changed (compared to the "
                "previous values of that communism ID): `amount`, `description`, `creator`, "
                "`active`. This prevents modifications of communism operations after "
                "creation. Use the other POST methods if possible instead. A 409 "
                "error will also be returned if a closed communism was altered."
)
def update_existing_communism(
        communism: schemas.Communism,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("update_existing_communism")


@router.get(
    "/{communism_id}",
    response_model=schemas.Communism,
    responses={404: {}},
    description="Return an existing communism. A 404 error will be returned "
                "if the specified communism ID was not found."
)
def get_communism_by_id(
        communism_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_communism_by_id")


@router.get(
    "/creator/{user_id}",
    response_model=List[schemas.Communism],
    responses={404: {}},
    description="Return a list of all communisms which have been created by the user with "
                "that `user_id`. A 404 error will be returned if the user ID is unknown."
)
def get_communisms_by_creator(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_communisms_by_creator")


@router.get(
    "/participant/{user_id}",
    response_model=List[schemas.Communism],
    responses={404: {}},
    description="Return a list of all communisms where the user with that `user_id` has "
                "participated in. A 404 error will be returned if the user ID is unknown."
)
def get_communisms_by_participant(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_communisms_by_participant")


@router.post(
    "/{communism_id}/accept",
    response_model=schemas.SuccessfulCommunism,
    responses={404: {}, 409: {}},
    description="Accept an existing communism operation. A 409 error will be returned if "
                "this is attempted on a closed/inactive communism operation. A 404 error "
                "will be returned if the specified `communism_id` is not known. This "
                "operation closes the communism and prevents any further changes. Note "
                "that this operation will implicitly also perform all transactions to "
                "and from all members of the communism, so take care. A frontend "
                "application might want to request explicit user approval before."
)
def accept_existing_communism(
        communism_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("accept_existing_communism")


@router.post(
    "/{communism_id}/cancel",
    response_model=schemas.Communism,
    responses={404: {}, 409: {}},
    description="Cancel an existing communism operation. A 409 error will be returned if "
                "this is attempted on a closed/inactive communism operation. A 404 error "
                "will be returned if the specified `communism_id` is not known. This "
                "operation closes the communism and prevents any further changes. "
                "No transactions will be performed based on this communism anymore."
)
def cancel_existing_communism(
        communism_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("cancel_existing_communism")
