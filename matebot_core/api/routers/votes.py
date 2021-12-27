"""
MateBot router module for /votes requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import Conflict, ReturnType
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
    Add a new vote to some open poll.

    A 404 error will be returned if either the user ID or the poll ID was
    not found. A 409 error will be returned if either the poll has already
    been closed, the user has already voted in the poll (use `PUT` to change
    votes), the user is not active or the poll refers to a refund request
    and the user is not marked as permitted to participate in refund request.

    If the poll refers to an open refund request, the refund request may be closed
    when the configured limits for accepting or declining the refund request are
    reached by the newly created vote. This behavior is implicit, i.e. this endpoint
    will just return the newly created vote regardless of any closed polls. Either
    listen for callbacks or query `GET /polls/{id}` afterwards to be sure. Take
    a look at `PUT /refunds` for more information about the closing process.
    """

    user = await helpers.return_one(vote.user_id, models.User, local.session)
    poll = await helpers.return_one(vote.poll_id, models.Poll, local.session)

    if poll.closed is not None:
        raise Conflict("Adding votes to already closed polls is illegal")
    if await helpers.return_all(models.Vote, local.session, poll=poll, user=user):
        raise Conflict(
            f"User {user.name!r} has already voted in this poll",
            str({"user": user, "poll": poll})
        )
    if not user.active:
        raise Conflict(
            f"User {user.name!r} is not active and can't participate in polls.",
            str({"user": user, "poll": poll})
        )

    refunds = await helpers.return_all(models.Refund, local.session, poll_id=poll.id)
    if len(refunds) == 0:  # no refund linked to this ballot
        model = models.Vote(
            user=user,
            poll=poll,
            vote=vote.vote
        )
        return await helpers.create_new_of_model(model, local, logger)

    if not user.permission:
        raise Conflict(
            f"User {user.name!r} is not permitted to participate in refund polls.",
            str({"user": user, "poll": poll})
        )

    model = models.Vote(
        user=user,
        poll=poll,
        vote=vote.vote
    )
    vote_schema = await helpers.create_new_of_model(model, local, logger)

    sum_of_votes = sum(v.vote for v in poll.votes)
    min_approves = local.config.general.min_refund_approves
    min_disapproves = local.config.general.min_refund_disapproves
    if sum_of_votes >= min_approves or -sum_of_votes >= min_disapproves:
        pass

    return vote_schema


@router.put(
    "",
    response_model=schemas.Vote,
    responses={k: {"model": schemas.APIError} for k in (403, 404, 409)}
)
@versioning.versions(minimal=1)
async def change_existing_vote(
        vote: schemas.Vote,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update the `vote` value of an existing vote.

    A 403 error will be returned if any other attribute than `vote` got changed.
    A 404 error will be returned if the vote ID is unknown. A 409 error
    will be returned if the poll isn't marked changeable (i.e. forbids changes).
    """

    model = await helpers.return_one(vote.id, models.Vote, local.session)
    helpers.restrict_updates(vote, model.schema)

    if not model.poll.changeable:
        raise Conflict("Updating the vote of a restricted poll is illegal", str(model.poll))

    model.vote = vote.vote
    return await helpers.update_model(model, local, logger, ReturnType.SCHEMA)


@router.delete(
    "",
    status_code=204,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def delete_existing_vote(
        vote: schemas.Vote,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing vote model.

    A 404 error will be returned if the vote can't be found. A 409 error
    will be returned if the poll is restricted, i.e. votes can't be
    removed from the ongoing poll as soon as they have been created,
    or if the poll has already been closed and the result was determined.
    """

    def hook(model: models.Vote, *_):
        if not model.poll.changeable:
            raise Conflict("Deleting the vote of a restricted poll is illegal", str(model.poll))
        if model.poll.closed or not model.poll.active:
            raise Conflict("Deleting the vote of a closed poll is illegal", str(model.poll))

    await helpers.delete_one_of_model(vote.id, models.Vote, local, logger=logger, hook_func=hook)


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
