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
            restricted=ballot.restricted
        ),
        local,
        logger
    )


@router.patch(
    "",
    response_model=schemas.Ballot,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def patch_existing_ballot(
        ballot: schemas.BallotPatch,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Close a ballot to calculate the result based on all votes.

    If the ballot has already been closed, this operation will
    do nothing and silently return the unmodified model.

    A 404 error will be returned if the ballot ID is not found.
    A 409 error will be returned if the ballot is used by some refund
    and this refund has not been closed yet, since this should
    be done first. Take a look at `PATCH /refunds` for details.
    """

    model = await helpers.return_one(ballot.id, models.Ballot, local.session)
    refund = local.session.query(models.Refund).filter_by(ballot_id=model.id).first()
    if refund and refund.active:
        raise Conflict(f"Ballot is used by refund {refund.id}", detail=str(refund))

    if model.closed is not None:
        local.entity.model_name = models.Ballot.__name__
        return local.attach_headers(model.schema)

    model.result = sum(v.vote for v in model.votes)
    model.active = False
    model.closed = datetime.datetime.now().replace(microsecond=0)

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA_WITH_TAG)


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
