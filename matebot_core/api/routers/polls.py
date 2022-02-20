"""
MateBot router module for /polls requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/polls", tags=["Polls"])


@router.get(
    "",
    response_model=List[schemas.Poll]
)
@versioning.versions(minimal=1)
async def get_all_polls(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all polls with all associated data, including the votes
    """

    return await helpers.get_all_of_model(models.Poll, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Poll,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(minimal=1)
async def create_new_membership_poll(
        poll: schemas.PollCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new membership request poll for the specified user

    A 400 error will be returned if the creator is already internal or disabled.
    A 404 error will be returned if the user ID of the `creator` is unknown.
    A 409 error will be returned if the special community user is the creator.
    """

    creator = await helpers.return_one(poll.creator_id, models.User, local.session)
    if creator.special:
        raise Conflict("A membership request can't be created for the community user.")
    if not creator.active:
        raise BadRequest("Your user account was disabled. Therefore, you can't create membership requests.")
    if not creator.external:
        raise BadRequest("You are already an internal user. Membership request polls can only be created by externals.")

    return await helpers.create_new_of_model(models.Poll(creator=creator), local, logger)


# @router.put(
#     "",
#     response_model=schemas.Poll,
#     responses={k: {"model": schemas.APIError} for k in (403, 404, 409)}
# )
# @versioning.versions(1)
# async def update_existing_poll(
#         poll: schemas.Poll,
#         local: LocalRequestData = Depends(LocalRequestData)
# ):
#     """
#     Update an existing poll model (and maybe calculate the
#     result based on all votes, when closing it).
#
#     A 403 error will be returned if any other attribute than `active` has
#     been changed. A 404 error will be returned if the poll ID is not found.
#     A 409 error will be returned if the poll is used by some refund
#     and this refund has not been closed yet, since this should
#     be done first. Take a look at `PUT /refunds` for details.
#     """
#
#     model = await helpers.return_one(poll.id, models.Poll, local.session)
#     helpers.restrict_updates(poll, model.schema)
#
#     refund = local.session.query(models.Refund).filter_by(poll_id=poll.id).first()
#     if refund and refund.active:
#         raise Conflict(f"Poll {poll.id} is used by active refund {refund.id}", detail=str(refund))
#
#     if model.active and not poll.active:
#         model.result = sum(v.vote for v in model.votes)
#         model.active = False
#         model.closed = datetime.datetime.now().replace(microsecond=0)
#         return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)
#
#     return await helpers.get_one_of_model(poll.id, models.Poll, local)


@router.get(
    "/{poll_id}",
    response_model=schemas.Poll,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_poll_by_id(
        poll_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the poll identified by a specific poll ID.

    A 404 error will be returned in case the poll ID is unknown.
    """

    return await helpers.get_one_of_model(poll_id, models.Poll, local)


@router.post(
    "/vote",
    response_model=schemas.PollVoteResponse,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(1)
async def vote_for_membership_request(
        vote: schemas.VoteCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Add a new vote for an open membership poll

    This endpoint will take care of promoting the creator to an internal
    user if enough votes for it have been created. On the other hand, it
    will also close the membership poll if enough votes against the proposal
    have been created. The limits are set in the server's configuration.

    A 400 error will be returned if the poll is not active anymore, the user has
    already voted in the specified ballot, the user is not active or unprivileged.
    A 404 error will be returned if the user ID or ballot ID is unknown.
    A 409 error will be returned if the voter is the community user, if an
    invalid state has been detected or the ballot referenced by the newly
    created vote is actually about a refund request instead of a membership poll.
    """

    user = await helpers.return_one(vote.user_id, models.User, local.session)
    ballot = await helpers.return_one(vote.ballot_id, models.Ballot, local.session)

    if user.special:
        raise Conflict("The community user can't vote in membership polls.")
    if ballot.refunds:
        raise Conflict("This endpoint ('POST /polls/vote') can't be used to vote on refund requests.")
    if not ballot.polls:
        raise Conflict("The ballot didn't reference any membership poll. Please file a bug report.", str(ballot))
    if len(ballot.polls) != 1:
        raise Conflict("The ballot didn't reference exactly one refund request. Please file a bug report.", str(ballot))
    poll: models.Poll = ballot.polls[0]

    if not poll.active:
        raise BadRequest("You can't vote on already closed membership polls.")
    if local.session.query(models.Vote).filter_by(ballot=ballot, user=user):
        raise BadRequest("You have already voted for this membership poll. You can't vote twice.")
    if not user.active:
        raise BadRequest("Your user account was disabled. Therefore, you can't vote for this membership poll.")
    if not user.permission:
        raise BadRequest("You are not permitted to participate in ballots about membership polls.")

    model = models.Vote(user=user, ballot=ballot, vote=vote.vote)
    await helpers.create_new_of_model(model, local, logger)

    result_of_ballot = ballot.result
    if result_of_ballot >= local.config.general.min_membership_approves:
        poll.active = False
        poll.accepted = True
        poll.creator.external = False
        await helpers.update_model(poll, local, logger)
        await helpers.update_model(poll.creator, local, logger)

    elif -result_of_ballot >= local.config.general.min_membership_disapproves:
        poll.active = False
        poll.accepted = False
        await helpers.update_model(poll, local, logger)

    return schemas.PollVoteResponse(poll=poll.schema, vote=model.schema)


@router.post(
    "/abort/{poll_id}",
    response_model=schemas.Poll,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def abort_open_membership_poll(
        poll_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an ongoing poll request (closing it without performing the transaction)

    A 400 error will be returned if the poll is already closed.
    A 404 error will be returned if the poll ID is unknown.
    """

    model = await helpers.return_one(poll_id, models.Poll, local.session)

    if not model.active:
        raise BadRequest("Updating an already closed poll is not possible.", detail=str(model))

    model.active = False
    logger.debug(f"Aborting poll {model}")
    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)
