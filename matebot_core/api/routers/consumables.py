"""
MateBot router module for /consumables requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
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
@versioning.versions(minimal=1)
async def get_all_consumables(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all current consumables.
    """

    return await helpers.get_all_of_model(models.Consumable, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Consumable,
    responses={409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def create_new_consumable(
        consumable: schemas.ConsumableCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new consumable.

    A 409 error will be returned when the name has already been taken.
    """

    values = consumable.dict()
    if local.session.query(models.Consumable).filter_by(name=values["name"]).all():
        raise Conflict(
            "Consumable can't be created since one with that name already exists.",
            f"Rejected consumable name: {values['name']!r}"
        )

    raw_messages = values.pop("messages")
    model = models.Consumable(**values)
    messages = [models.ConsumableMessage(message=msg, consumable=model) for msg in raw_messages]
    return await helpers.create_new_of_model(model, local, logger, "/consumables/{}", True, messages)


@router.put(
    "",
    response_model=schemas.Consumable,
    responses={k: {"model": schemas.APIError} for k in (403, 404, 409)}
)
@versioning.versions(minimal=1)
async def update_existing_consumable(
        consumable: schemas.Consumable,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing consumable model.

    A 403 error will be returned if the `modified` field has been changed.
    A 404 error will be returned if the `id` doesn't exist.
    A 409 error will be returned when the name has already been taken.
    """

    model = await helpers.return_one(consumable.id, models.Consumable, local.session)
    helpers.restrict_updates(consumable, model.schema)

    await helpers.expect_none(models.Consumable, local.session, name=consumable.name)

    model.name = consumable.name
    model.description = consumable.description
    model.price = consumable.price
    model.symbol = consumable.symbol
    model.stock = consumable.stock

    for m in model.messages:
        local.session.delete(m)

    model.messages = [
        models.ConsumableMessage(message=m, consumable_id=model.id) for m in consumable.messages
    ]

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)


@router.delete(
    "",
    status_code=204,
    responses={k: {"model": schemas.APIError} for k in (404, 409, 412)}
)
@versioning.versions(minimal=1)
async def delete_existing_consumable(
        consumable: schemas.Consumable,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing consumable model.

    A 404 error will be returned if the requested `id` doesn't exist.
    A 409 error will be returned if the object is not up-to-date, which
    means that the user agent needs to get the object before proceeding.
    A 412 error will be returned if the conditional request fails.
    """

    await helpers.delete_one_of_model(
        consumable.id,
        models.Consumable,
        local,
        schema=consumable,
        logger=logger
    )


@router.get(
    "/{consumable_id}",
    response_model=schemas.Consumable,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_consumable_by_id(
        consumable_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the consumable model of a specific consumable ID.

    A 404 error will be returned in case the consumable ID is unknown.
    """

    return await helpers.get_one_of_model(consumable_id, models.Consumable, local)
