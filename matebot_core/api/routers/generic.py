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
    def _get(model: Type[models.Base]) -> uuid.UUID:
        all_objects = [obj.schema for obj in local.session.query(model).all()]
        return uuid.UUID(local.entity.make_etag(all_objects, model.__name__))

    return schemas.Updates(
        aliases=_get(models.UserAlias),
        applications=_get(models.Application),
        ballots=_get(models.Ballot),
        communisms=_get(models.Communism),
        refunds=_get(models.Refund),
        transactions=_get(models.Transaction),
        users=_get(models.User),
        votes=_get(models.Vote),
        timestamp=datetime.datetime.now().timestamp()
    )
