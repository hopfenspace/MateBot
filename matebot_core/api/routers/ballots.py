"""
MateBot router module for /ballots requests
"""

import logging
from typing import List

from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from ... import schemas
from ...persistence import models


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/ballots",
    tags=["Ballots"]
)


@router.get(
    "",
    response_model=List[schemas.Ballot],
    description="Return a list of all ballots with all associated data, including the votes."
)
def get_all_ballots(local: LocalRequestData = Depends(LocalRequestData)):
    all_ballots = [b.schema for b in local.session.query(models.Ballot).all()]
    local.entity.model_name = schemas.Ballot.__name__
    local.entity.compare(all_ballots)
    return local.attach_headers(all_ballots)


@router.post(
    "",
    response_model=schemas.Ballot,
    description="Add a new ballot based on the given data and create a new ID for it."
)
def add_new_ballot(
        ballot: schemas.IncomingBallot,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("add_new_ballot")


@router.patch(
    "/{ballot_id}",
    response_model=schemas.Ballot,
    responses={404: {}, 409: {}},
    description="Close a ballot to calculate the result based on all votes. "
                "A 404 error will be returned if the ballot ID is not found. "
                "A 409 error will be returned if the ballot is already closed."
)
def close_ballot(ballot_id: int, local: LocalRequestData = Depends(LocalRequestData)):
    raise MissingImplementation("close_ballot")
