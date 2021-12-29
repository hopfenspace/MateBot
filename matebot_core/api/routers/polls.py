"""
MateBot router module for /polls requests
"""

import logging
import datetime
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
    prefix="/polls",
    tags=["Polls"]
)


@router.get(
    "",
    response_model=List[schemas.Poll]
)
@versioning.versions(minimal=1)
async def get_all_polls(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all polls with all associated data, including the votes.
    """

    return await helpers.get_all_of_model(models.Poll, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Poll
)
@versioning.versions(minimal=1)
async def add_new_poll(
        poll: schemas.PollCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Add a new poll based on the given data and create a new ID for it.
    """

    return await helpers.create_new_of_model(
        models.Poll(
            question=poll.question,
            changeable=poll.changeable
        ),
        local,
        logger
    )


@router.put(
    "",
    response_model=schemas.Poll,
    responses={k: {"model": schemas.APIError} for k in (403, 404, 409)}
)
@versioning.versions(1)
async def update_existing_poll(
        poll: schemas.Poll,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing poll model (and maybe calculate the
    result based on all votes, when closing it).

    A 403 error will be returned if any other attribute than `active` has
    been changed. A 404 error will be returned if the poll ID is not found.
    A 409 error will be returned if the poll is used by some refund
    and this refund has not been closed yet, since this should
    be done first. Take a look at `PUT /refunds` for details.
    """

    model = await helpers.return_one(poll.id, models.Poll, local.session)
    helpers.restrict_updates(poll, model.schema)

    refund = local.session.query(models.Refund).filter_by(poll_id=poll.id).first()
    if refund and refund.active:
        raise Conflict(f"Poll {poll.id} is used by active refund {refund.id}", detail=str(refund))

    if model.active and not poll.active:
        model.result = sum(v.vote for v in model.votes)
        model.active = False
        model.closed = datetime.datetime.now().replace(microsecond=0)
        return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)

    return await helpers.get_one_of_model(poll.id, models.Poll, local)


@router.get(
    "/{poll_id}",
    response_model=schemas.Poll,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_poll_by_id(
        poll_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the poll identified by a specific poll ID.

    A 404 error will be returned in case the poll ID is unknown.
    """

    return await helpers.get_one_of_model(poll_id, models.Poll, local)
