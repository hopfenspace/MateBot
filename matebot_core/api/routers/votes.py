"""
MateBot router module for /votes requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import Conflict, MissingImplementation
from ..dependency import LocalRequestData
from .. import helpers, versioning
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
@versioning.versions(minimal=1)
async def get_all_votes(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known votes.
    """

    return await helpers.get_all_of_model(models.Vote, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Vote,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
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

    user = await helpers.return_one(vote.user_id, models.User, local.session)
    ballot = await helpers.return_one(vote.ballot_id, models.Ballot, local.session)

    if ballot.closed is not None:
        raise Conflict("Adding votes to already closed ballots is illegal")
    if await helpers.return_all(models.Vote, local.session, ballot=ballot, user=user):
        raise Conflict(
            f"User {user.name!r} has already voted in this ballot",
            str({"user": user, "ballot": ballot})
        )

    model = models.Vote(
        user=user,
        ballot=ballot,
        vote=vote.vote
    )
    return await helpers.create_new_of_model(model, local, logger)


@router.patch(
    "",
    response_model=schemas.Vote,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def change_existing_vote(
        vote: schemas.VotePatch,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update the `vote` value of an existing vote.

    A 404 error will be returned if the vote ID is unknown. A 409 error
    will be returned if the ballot is restricted (i.e. forbids changes).
    """

    model = await helpers.return_one(vote.id, models.Vote, local.session)
    if model.ballot.restricted:
        raise Conflict("Updating the vote of a restricted ballot is illegal", str(model.ballot))

    if not vote.vote:
        local.entity.model_name = models.Vote.__name__
        return local.attach_headers(model.schema)

    model.vote = vote.vote
    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA_WITH_TAG)


@router.delete(
    "",
    status_code=201,
    responses={
        403: {"model": schemas.APIError},
        404: {"model": schemas.APIError},
        409: {"model": schemas.APIError}
    }
)
@versioning.versions(minimal=1)
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
@versioning.versions(1)
async def get_vote_by_id(
        vote_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return details about a specific vote identified by its `vote_id`.

    A 404 error will be returned if that ID is unknown.
    """

    return await helpers.get_one_of_model(vote_id, models.Vote, local)
