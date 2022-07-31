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


@callback_router.post("/", name="Publish Events")
def send_callback_query(events: schemas.EventsNotification):  # noqa
    """
    Publish a list of recent events to a callback listener

    It's up to the developer of the application that wants to use
    callbacks to implement this endpoint. Those requests may be ignored.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    However, if the external API doesn't react or connecting fails, the
    MateBot core server will occasionally try to resend the event.
    """


@router.get("/callbacks", tags=["Callbacks"], response_model=List[schemas.Callback], callbacks=callback_router.routes)
@versioning.versions(minimal=1)
async def search_for_callbacks(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        url: Optional[pydantic.constr(max_length=255)] = None,
        application_id: Optional[pydantic.NonNegativeInt] = None,
        limit: Optional[pydantic.NonNegativeInt] = None,
        page: Optional[pydantic.NonNegativeInt] = None,
        descending: Optional[bool] = False,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all callbacks that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.Callback,
        local,
        limit=limit,
        page=page,
        descending=descending,
        id=id,
        url=url,
        application_id=application_id
    )


@router.post(
    "/callbacks",
    tags=["Callbacks"],
    status_code=201,
    response_model=schemas.Callback,
    responses={400: {"model": schemas.APIError}, 409: {"model": schemas.APIError}},
    callbacks=callback_router.routes
)
@versioning.versions(minimal=1)
async def create_new_callback(
        callback: schemas.CallbackCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Add a new callback API which should implement all required endpoints

    * `400`: if the `application_id` is not known
    * `409`: if the same URL has already been registered for another application
    """

    if callback.application_id is not None:
        await helpers.return_one(callback.application_id, models.Application, local.session)
    matches = local.session.query(models.Callback).filter_by(url=callback.url).all()
    if matches:
        raise Conflict("A callback with that URL already exists, but the base URL must be unique.", str(matches))

    model = models.Callback(
        url=callback.url,
        application_id=callback.application_id,
        shared_secret=callback.shared_secret
    )
    local.session.add(model)
    local.session.commit()
    return model.schema


@router.delete(
    "/callbacks",
    tags=["Callbacks"],
    status_code=204,
    responses={400: {"model": schemas.APIError}},
    callbacks=callback_router.routes
)
@versioning.versions(minimal=1)
async def delete_existing_callback(
        body: schemas.IdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing callback model

    * `400`: if the requested callback ID doesn't exist
    """

    return await helpers.delete_one_of_model(body.id, models.Callback, local, logger=logger)
