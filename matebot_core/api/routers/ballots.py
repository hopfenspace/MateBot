"""
MateBot router module for /ballots requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from .. import helpers
from ...persistence import models
from ... import schemas


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
    return helpers.get_all_of_model(models.Ballot, local)


@router.post(
    "",
    response_model=schemas.Ballot,
    description="Add a new ballot based on the given data and create a new ID for it."
)
def add_new_ballot(
        ballot: schemas.BallotCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("add_new_ballot")


@router.patch(
    "/{ballot_id}",
    response_model=schemas.Ballot,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}},
    description="Close a ballot to calculate the result based on all votes. "
                "A 404 error will be returned if the ballot ID is not found. "
                "A 409 error will be returned if the ballot is already closed."
)
def close_ballot(
        ballot_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("close_ballot")


@router.get(
    "/{ballot_id}",
    response_model=schemas.Ballot,
    responses={404: {"model": schemas.APIError}},
    description="Return the ballot of a specific ballot ID. A 404 "
                "error will be returned in case the ballot ID is unknown."
)
def get_ballot_by_id(
        ballot_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    return helpers.get_one_of_model(ballot_id, models.Ballot, local)
