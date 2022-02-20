"""
MateBot router module for /ballots
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ballots", tags=["Ballots"])


@router.get(
    "",
    response_model=List[schemas.Ballot]
)
@versioning.versions(minimal=1)
async def get_all_ballots(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known ballots
    """

    return await helpers.get_all_of_model(models.Ballot, local)


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
    Return details about a specific ballot identified by its `ballot_id`

    A 404 error will be returned if that ID is unknown.
    """

    return await helpers.get_one_of_model(ballot_id, models.Ballot, local)
