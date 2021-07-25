"""
MateBot router module for various different requests without specialized purpose
"""

import logging

from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Generic"]
)


@router.get(
    "/status",
    response_model=schemas.Status,
    description="Return some information about the current status "
                "of the server, the database and whatsoever."
)
def get_status(local: LocalRequestData = Depends(LocalRequestData)):
    raise MissingImplementation("get_status")


@router.get(
    "/updates",
    response_model=schemas.Updates,
    description="Return a collection of the current ETags of all available, important models to "
                "determine whether any of them has changed in them meantime. This allows "
                "user agents to implement polling. Of course, caching is required for that."
)
def get_updates(local: LocalRequestData = Depends(LocalRequestData)):
    raise MissingImplementation("get_updates")
