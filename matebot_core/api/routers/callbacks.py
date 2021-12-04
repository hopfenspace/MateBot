"""
MateBot router for the callback API and for /callbacks requests
"""

import logging
from typing import List

from fastapi import APIRouter, Depends

from ..base import Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

callback_router = APIRouter(
    tags=["Announcements"]
)


@callback_router.get("/refresh")
def trigger_cache_refresh():
    """
    Trigger a refresh of the local object caches.

    This endpoint must be present on the external API, since it will always
    be called when some internal states of the MateBot core have changed.
    It will be called before the other, more specific endpoints below.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


@callback_router.get("/create/{model}/{id}")
def announce_created_model():
    """
    Announce a created object of the `model` with the `id`.

    This endpoint may be seen as optional, since the external API is not
    strictly required to implement this endpoint (but a meaningful error,
    like 404, should be returned, of course). The endpoint will be called
    after the response to the `/trigger` request has arrived.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


@callback_router.get("/update/{model}/{id}")
def announce_updated_model():
    """
    Announce an updated object of the `model` with the `id`.

    This endpoint may be seen as optional, since the external API is not
    strictly required to implement this endpoint (but a meaningful error,
    like 404, should be returned, of course). The endpoint will be called
    after the response to the `/trigger` request has arrived.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


@callback_router.get("/delete/{model}/{id}")
def announce_deleted_model():
    """
    Announce a deleted object of the `model` with the `id`.

    This endpoint may be seen as optional, since the external API is not
    strictly required to implement this endpoint (but a meaningful error,
    like 404, should be returned, of course). The endpoint will be called
    after the response to the `/trigger` request has arrived.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


router = APIRouter(
    prefix="/callbacks",
    tags=["Callbacks"]
)


@router.get(
    "",
    response_model=List[schemas.Callback],
    callbacks=callback_router.routes
)
@versioning.versions(minimal=1)
async def get_all_callbacks(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all currently registered (and therefore enabled) callback APIs.
    """

    return await helpers.get_all_of_model(models.Callback, local)


@router.post(
    "",
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
    Add a new callback API which should implement all required endpoints.

    A 404 error will be returned if the `app_id` is not known.
    A 409 error will be returned when the exact same base URL
    has already been registered for any application.
    """

    if callback.app is not None:
        await helpers.return_one(callback.app, models.Application, local.session)
    uri = callback.base + ("/" if not callback.base.endswith("/") else "")
    await helpers.expect_none(models.Callback, local.session, base=uri)

    model = models.Callback(
        base=uri,
        app_id=callback.app,
        username=callback.username,
        password=callback.password
    )
    return await helpers.create_new_of_model(model, local, logger)


@router.put(
    "",
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
    Update an existing callback model identified by its `id`.

    A 404 error will be returned if the callback `id` doesn't exist.
    A 409 error will be returned when the exact same base URL is already in use.
    """

    model = await helpers.return_one(callback.id, models.Callback, local.session)
    helpers.restrict_updates(callback, model.schema)

    if await helpers.expect_none(models.Callback, local.session, base=callback.base):
        raise Conflict(f"Base URL {callback.base} already in use.", detail=str(callback))

    model.base = callback.base
    model.username = callback.username
    model.password = callback.password

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA_WITH_TAG)


@router.delete(
    "",
    status_code=204,
    responses={k: {"model": schemas.APIError} for k in (404, 409, 412)},
    callbacks=callback_router.routes
)
@versioning.versions(minimal=1)
async def delete_existing_callback(
        callback: schemas.Callback,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing callback model.

    A 404 error will be returned if the requested `id` doesn't exist.
    A 409 error will be returned if the object is not up-to-date, which
    means that the user agent needs to get the object before proceeding.
    A 412 error will be returned if the conditional request fails.
    """

    await helpers.delete_one_of_model(
        callback.id,
        models.Callback,
        local,
        schema=callback,
        logger=logger
    )
