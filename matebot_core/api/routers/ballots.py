"""
MateBot router module for /ballots requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import MissingImplementation
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
            restricted=ballot.restricted
        ),
        local,
        logger
    )


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


@router.patch(
    "/{ballot_id}",
    response_model=schemas.Ballot,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def close_ballot_by_id(
        ballot_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Close a ballot to calculate the result based on all votes.

    If the ballot has already been closed, this operation will
    do nothing and silently return the unmodified model.
    Note that if any refund makes use of this ballot, then this
    refund will also be closed implicitly by closing its ballot.
    This will also make its transaction(s), if the ballot was
    successful. Take a look at `PATCH /refunds` for details.

    A 404 error will be returned if the ballot ID is not found.
    """

    raise MissingImplementation("close_ballot_by_id")
