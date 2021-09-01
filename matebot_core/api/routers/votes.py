"""
MateBot router module for /votes requests
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
    prefix="/votes",
    tags=["Votes"]
)


@router.get(
    "",
    response_model=List[schemas.Vote]
)
async def get_all_votes(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known votes.
    """

    return helpers.get_all_of_model(models.Vote, local)


@router.post(
    "",
    response_model=schemas.Vote,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
async def add_new_vote(
        vote: schemas.VoteCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Add a new vote to some open ballot.

    A 404 error will be returned if either the user ID or the ballot ID was
    not found. A 409 error will be returned if either the ballot has already been
    closed or the user has already voted in the ballot (use `PUT` to change votes).
    """

    raise MissingImplementation("add_new_vote")


@router.put(
    "",
    response_model=schemas.Vote,
    responses={
        403: {"model": schemas.APIError},
        404: {"model": schemas.APIError},
        409: {"model": schemas.APIError}
    }
)
async def change_existing_vote(
        vote: schemas.Vote,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update the `vote` value of an existing vote.

    Note that this method only accepts changes to the `vote` field.

    A 409 error will be returned if the `modified` field was changed or if the
    combination of `user_id` and `ballot_id` doesn't match the specified `id`
    of the vote. A 404 error will be returned if the vote ID is unknown. A 403
    error will be returned if the ballot is restricted (i.e. forbids changes).
    """

    raise MissingImplementation("change_existing_vote")


@router.delete(
    "",
    status_code=201,
    responses={
        403: {"model": schemas.APIError},
        404: {"model": schemas.APIError},
        409: {"model": schemas.APIError}
    }
)
async def delete_existing_vote(
        vote: schemas.Vote,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing vote identified by its `id`.

    A 409 error will be returned if the combination of `user_id` and `ballot_id`
    doesn't match the specified `id`. A 404 error will be returned if the vote
    ID is unknown. A 403 error will be returned if the ballot is restricted, i.e.
    votes can't be removed from the ongoing ballot as soon as they have been created.
    """

    raise MissingImplementation("delete_existing_vote")


@router.get(
    "/{vote_id}",
    response_model=schemas.Vote,
    responses={404: {"model": schemas.APIError}}
)
async def get_vote_by_id(
        vote_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return details about a specific vote identified by its `vote_id`.

    A 404 error will be returned if that ID is unknown.
    """

    return helpers.get_one_of_model(vote_id, models.Vote, local)
