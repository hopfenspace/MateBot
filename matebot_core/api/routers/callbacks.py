"""
MateBot router for the callback API and for /callbacks requests
"""

import logging

from fastapi import APIRouter, Depends


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
    Announce a created object of the ``model`` with the ``id``.

    This endpoint may be seen as optional, since the external API is not
    strictly required to implement this endpoint (but a meaningful error,
    like 404, should be returned, of course). The endpoint will be called
    after the response to the ``/trigger`` request has arrived.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


@callback_router.get("/update/{model}/{id}")
def announce_updated_model():
    """
    Announce an updated object of the ``model`` with the ``id``.

    This endpoint may be seen as optional, since the external API is not
    strictly required to implement this endpoint (but a meaningful error,
    like 404, should be returned, of course). The endpoint will be called
    after the response to the ``/trigger`` request has arrived.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


@callback_router.get("/delete/{model}/{id}")
def announce_deleted_model():
    """
    Announce a deleted object of the ``model`` with the ``id``.

    This endpoint may be seen as optional, since the external API is not
    strictly required to implement this endpoint (but a meaningful error,
    like 404, should be returned, of course). The endpoint will be called
    after the response to the ``/trigger`` request has arrived.

    Implementation detail: The response of the external API implementation
    will be logged in case of an error, but will be ignored in general.
    The external API does not need to return any meaningful response.
    """


router = APIRouter(
    prefix="/callbacks",
    tags=["Callbacks"]
)
