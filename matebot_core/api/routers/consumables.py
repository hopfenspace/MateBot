"""
MateBot router module for /consumables requests
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
    prefix="/consumables",
    tags=["Consumables"]
)


@router.get(
    "",
    response_model=List[schemas.Consumable]
)
def get_all_consumables(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all current consumables.
    """

    return helpers.get_all_of_model(models.Consumable, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Consumable,
    responses={409: {"model": schemas.APIError}}
)
def create_new_consumable(
        consumable: schemas.ConsumableCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new consumable.

    A 409 error will be returned when the name has already been taken.
    """

    raise MissingImplementation("create_new_consumable")


@router.put(
    "",
    response_model=schemas.Consumable,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
def update_existing_consumable(
        consumable: schemas.ConsumableUpdate,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing consumable model.

    A 404 error will be returned if the `id` doesn't exist.
    A 409 error will be returned when the name has already been taken.
    """

    raise MissingImplementation("update_existing_consumable")


@router.delete(
    "",
    status_code=204,
    responses={404: {"model": schemas.APIError}}
)
def delete_existing_consumable(
        consumable: schemas.Consumable,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing consumable model.

    A 404 error will be returned if the `id` doesn't exist.
    """

    raise MissingImplementation("delete_existing_consumable")


@router.get(
    "/{consumable_id}",
    response_model=schemas.Consumable,
    responses={404: {"model": schemas.APIError}}
)
def get_consumable_by_id(
        consumable_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the consumable model of a specific consumable ID.

    A 404 error will be returned in case the consumable ID is unknown.
    """

    return helpers.get_one_of_model(consumable_id, models.Consumable, local)
