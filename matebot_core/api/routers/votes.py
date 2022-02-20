"""
MateBot router module for /votes requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import BadRequest, Conflict, ReturnType
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.refunds import close_refund
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/votes", tags=["Votes"])


@router.get(
    "",
    response_model=List[schemas.Vote]
)
@versioning.versions(minimal=1)
async def get_all_votes(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known votes
    """

    return await helpers.get_all_of_model(models.Vote, local)




@router.get(
    "/{vote_id}",
    response_model=schemas.Vote,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_vote_by_id(
        vote_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return details about a specific vote identified by its `vote_id`

    A 404 error will be returned if that ID is unknown.
    """

    return await helpers.get_one_of_model(vote_id, models.Vote, local)
