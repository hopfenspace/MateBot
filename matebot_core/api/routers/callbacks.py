"""
MateBot router for the callback API and for /callbacks requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import APIRouter, Depends

from ._router import router
from ..base import Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

callback_router = APIRouter(tags=["Announcements"])


@callback_router.get("/create/{model}/{id}", name="Announce-Creation")
def announce_created_model():
    """
    Announce a created object of the `model` with the `id`.

    It's up to the developer of the application that wants to use
    callbacks to implement this endpoint. Those requests may be ignored.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


@callback_router.get("/update/{model}/{id}", name="Announce-Update")
def announce_updated_model():
    """
    Announce an updated object of the `model` with the `id`.

    It's up to the developer of the application that wants to use
    callbacks to implement this endpoint. Those requests may be ignored.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


@callback_router.get("/delete/{model}/{id}", name="Announce-Deletion")
def announce_deleted_model():
    """
    Announce a deleted object of the `model` with the `id`.

    It's up to the developer of the application that wants to use
    callbacks to implement this endpoint. Those requests may be ignored.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


@router.get("/callbacks", tags=["Callbacks"], response_model=List[schemas.Callback], callbacks=callback_router.routes)
@versioning.versions(minimal=1)
async def search_for_callbacks(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        base: Optional[pydantic.constr(max_length=255)] = None,
        application_id: Optional[pydantic.NonNegativeInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all callbacks that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.Callback,
        local,
        id=id,
        base=base,
        application_id=application_id
    )


@router.post(
    "/callbacks",
    tags=["Callbacks"],
    status_code=201,
    response_model=schemas.Callback,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}},
    callbacks=callback_router.routes
)
@versioning.versions(minimal=1)
async def create_new_callback(
        callback: schemas.CallbackCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Add a new callback API which should implement all required endpoints

    * `404`: if the `application_id` is not known
    * `409`: if the exact same base URL has already been registered for any other application
    """

    if callback.application_id is not None:
        await helpers.return_one(callback.application_id, models.Application, local.session)
    uri = callback.base + ("/" if not callback.base.endswith("/") else "")
    matches = local.session.query(models.Callback).filter_by(base=uri).all()
    if matches:
        raise Conflict(f"A callback with that base URI already exists, but the base URI must be unique.", str(matches))

    model = models.Callback(
        base=uri,
        application_id=callback.application_id,
        username=callback.username,
        password=callback.password
    )
    return await helpers.create_new_of_model(model, local, logger)


@router.put(
    "/callbacks",
    tags=["Callbacks"],
    response_model=schemas.Callback,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}},
    callbacks=callback_router.routes
)
@versioning.versions(minimal=1)
async def update_existing_callback(
        callback: schemas.Callback,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing callback model identified by its `id`

    * `404`: if the callback ID doesn't exist
    * `409`: if the exact same base URL is already in use
    """

    model = await helpers.return_one(callback.id, models.Callback, local.session)
    if [m for m in local.session.query(models.Callback).filter_by(base=callback.base).all() if m.id != model.id]:
        raise Conflict(f"Base URL {callback.base} already in use.", detail=str(callback))

    model.base = callback.base
    model.application_id = callback.application_id
    model.username = callback.username
    model.password = callback.password

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)


@router.delete(
    "/callbacks",
    tags=["Callbacks"],
    status_code=204,
    responses={k: {"model": schemas.APIError} for k in (404, 409)},
    callbacks=callback_router.routes
)
@versioning.versions(minimal=1)
async def delete_existing_callback(
        callback: schemas.Callback,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing callback model

    * `404`: if the requested callback ID doesn't exist
    """

    return await helpers.delete_one_of_model(callback.id, models.Callback, local, logger=logger)
