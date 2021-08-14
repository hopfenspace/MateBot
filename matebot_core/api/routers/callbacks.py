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
    """


@callback_router.get("/create/{model}/{id}")
def announce_created_model():
    """
    Announce a created object of the ``model`` with the ``id``.
    """


@callback_router.get("/update/{model}/{id}")
def announce_updated_model():
    """
    Announce a updated object of the ``model`` with the ``id``.
    """


@callback_router.get("/delete/{model}/{id}")
def announce_deleted_model():
    """
    Announce a deleted object of the ``model`` with the ``id``.
    """


router = APIRouter(
    prefix="/callbacks",
    tags=["Callbacks"]
)
