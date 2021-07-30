"""
MateBot router module for /communisms requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from .. import helpers
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
    return helpers.get_all_of_model(models.Communism, local)


@router.post(
    "",
    response_model=schemas.Communism,
    responses={404: {}},
    description="Create a new communism based on the specified data. A 404 error will be "
                "returned if the user ID of the creator of that communism is unknown."
)
def create_new_communism(
        communism: schemas.CommunismCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("create_new_communism")


@router.patch(
    "",
    response_model=schemas.Communism,
    responses={404: {}, 409: {}},
    description="Change certain pieces of mutable information about an already existing "
                "communism. A 404 error will be returned if the communism ID was not "
                "found. A 409 error will be returned if a closed communism was altered "
                "or if the field `active` was set to `false` without also setting the "
                "field `accepted` to a non-null value. The mechanism of setting `active` "
                "to `false` is used to accept or close communisms. The fields `externals` "
                "and `participants` will be used as-is to update the internal state of "
                "the communism (which will be returned afterwards). Note that duplicate "
                "entries in the `participants` list will just be silently ignored."
)
def update_existing_communism(
        communism: schemas.CommunismPatch,
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
