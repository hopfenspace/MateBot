"""
MateBot router module for /ballots requests
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
    prefix="/ballots",
    tags=["Ballots"]
)


@router.get(
    "",
    response_model=List[schemas.Ballot]
)
@versioning.versions(minimal=1)
async def get_all_ballots(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all ballots with all associated data, including the votes.
    """

    return await helpers.get_all_of_model(models.Ballot, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Ballot
)
@versioning.versions(minimal=1)
async def add_new_ballot(
        ballot: schemas.BallotCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Add a new ballot based on the given data and create a new ID for it.
    """

    return await helpers.create_new_of_model(
        models.Ballot(
            question=ballot.question,
            changeable=ballot.changeable
        ),
        local,
        logger
    )


@router.put(
    "",
    response_model=schemas.Ballot,
    responses={k: {"model": schemas.APIError} for k in (403, 404, 409)}
)
@versioning.versions(1)
async def update_existing_ballot(
        ballot: schemas.Ballot,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing ballot model (and maybe calculate the
    result based on all votes, when closing it).

    A 403 error will be returned if any other attribute than `active` has
    been changed. A 404 error will be returned if the ballot ID is not found.
    A 409 error will be returned if the ballot is used by some refund
    and this refund has not been closed yet, since this should
    be done first. Take a look at `PUT /refunds` for details.
    """

    ballot_model = await helpers.return_one(ballot.id, models.Ballot, local.session)
    helpers.restrict_updates(ballot, ballot_model.schema)

    refund = local.session.query(models.Refund).filter_by(ballot_id=ballot.id).first()
    if refund and refund.active:
        raise Conflict(f"Ballot {ballot.id} is used by active refund {refund.id}", detail=str(refund))

    if ballot_model.active and not ballot.active:
        ballot_model.result = sum(v.vote for v in ballot_model.votes)
        ballot_model.active = False
        ballot_model.closed = datetime.datetime.now().replace(microsecond=0)
        return await helpers.update_model(ballot_model, local, logger, helpers.ReturnType.SCHEMA_WITH_TAG)

    return await helpers.get_one_of_model(ballot.id, models.Ballot, local)


@router.get(
    "/{ballot_id}",
    response_model=schemas.Ballot,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_ballot_by_id(
        ballot_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the ballot identified by a specific ballot ID.

    A 404 error will be returned in case the ballot ID is unknown.
    """

    return await helpers.get_one_of_model(ballot_id, models.Ballot, local)
