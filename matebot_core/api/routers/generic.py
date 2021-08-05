"""
MateBot router module for various different requests without specialized purpose
"""

import uuid
import logging
import datetime
from typing import Type

from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from ... import schemas
from ...persistence import models


logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Generic"]
)


@router.get(
    "/status",
    response_model=schemas.Status
)
def get_status(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return some information about the current status of the server, the database and whatsoever.
    """

    raise MissingImplementation("get_status")


@router.get(
    "/updates",
    response_model=schemas.Updates
)
def get_updates(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a collection of the current ETags of all important model collections.

    This operation can be used to determine whether any of the available models
    has changed in them meantime. This allows user agents to implement polling.
    Of course, user-agent caching is required for that. An alternative way to
    stay informed about updates are HTTP callbacks, which will be introduced later.
    """

    def _get(model: Type[models.Base]) -> uuid.UUID:
        all_objects = [obj.schema for obj in local.session.query(model).all()]
        return uuid.UUID(local.entity.make_etag(all_objects, model.__name__))

    return schemas.Updates(
        aliases=_get(models.UserAlias),
        applications=_get(models.Application),
        ballots=_get(models.Ballot),
        communisms=_get(models.Communism),
        consumables=_get(models.Consumable),
        refunds=_get(models.Refund),
        transactions=_get(models.Transaction),
        users=_get(models.User),
        votes=_get(models.Vote),
        timestamp=datetime.datetime.now().timestamp()
    )
