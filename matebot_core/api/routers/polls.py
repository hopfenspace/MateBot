"""
MateBot router module for /polls requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import Depends

from ._router import router
from ..base import BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...misc.notifier import Callback
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)


@router.get("/polls", tags=["Polls"], response_model=List[schemas.Poll])
@versioning.versions(minimal=1)
async def search_for_polls(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        active: Optional[bool] = None,
        accepted: Optional[bool] = None,
        creator_id: Optional[pydantic.NonNegativeInt] = None,
        ballot_id: Optional[pydantic.NonNegativeInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all polls that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.Poll,
        local,
        id=id,
        active=active,
        accepted=accepted,
        creator_id=creator_id,
        ballot_id=ballot_id
    )


@router.post(
    "/polls",
    tags=["Polls"],
    status_code=201,
    response_model=schemas.Poll,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
)
@versioning.versions(minimal=1)
async def create_new_membership_poll(
        poll: schemas.PollCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new membership request poll for the specified user

    * `400`: if the creator is already internal or disabled
        or the creator user specification couldn't be resolved
    * `409`: if the special community user is the creator
    """

    creator = await helpers.resolve_user_spec(poll.creator, local)
    if creator.special:
        raise Conflict("A membership request can't be created for the community user.")
    if not creator.active:
        raise BadRequest("This user account has been disabled. Therefore, you can't create membership requests.")
    if not creator.external:
        raise BadRequest("You are already an internal user. Membership request polls can only be created by externals.")

    model = models.Poll(creator=creator, ballot=models.Ballot())
    local.session.add(model)
    local.session.commit()

    Callback.push(
        schemas.EventType.POLL_CREATED,
        {"id": model.id, "user": model.creator_id}
    )
    return model.schema


@router.post(
    "/polls/vote",
    tags=["Polls"],
    response_model=schemas.PollVoteResponse,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
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

    * `400`: if the poll is not active anymore, the user has already voted
        in the specified ballot, the ballot wasn't found, the user is not active
        or unprivileged or if the voter's user specification couldn't be resolved
    * `409`: if the voter is the community user, an invalid state has
        been detected or the ballot referenced by the newly created vote
        is actually about a refund request instead of a membership poll
    """

    user = await helpers.resolve_user_spec(vote.user, local)
    ballot = await helpers.return_one(vote.ballot_id, models.Ballot, local.session)

    if user.special:
        raise Conflict("The community user can't vote in membership polls.")
    if ballot.refunds:
        raise Conflict("This endpoint can't be used to vote on refund requests.", "Try 'POST /refunds/vote' instead!")
    if not ballot.polls:
        raise Conflict("The ballot didn't reference any membership poll. Please file a bug report.", str(ballot))
    if len(ballot.polls) != 1:
        raise Conflict("The ballot didn't reference exactly one refund request. Please file a bug report.", str(ballot))
    poll: models.Poll = ballot.polls[0]

    if not poll.active:
        raise BadRequest("You can't vote on already closed membership polls.")
    if local.session.query(models.Vote).filter_by(ballot=ballot, user=user).all():
        raise BadRequest("You have already voted for this membership poll. You can't vote twice.")
    if not user.active:
        raise BadRequest("This user account has been disabled. Therefore, you can't vote for this membership poll.")
    if not user.permission:
        raise BadRequest("You are not permitted to participate in ballots about membership polls.")
    if user.id == poll.creator_id:
        raise BadRequest("You can't vote on your own membership polls.")

    model = models.Vote(user=user, ballot=ballot, vote=vote.vote)
    local.session.add(model)
    local.session.commit()
    Callback.push(
        schemas.EventType.POLL_UPDATED,
        {"id": model.id, "last_vote": model.id, "current_result": ballot.result}
    )

    result_of_ballot = ballot.result
    if result_of_ballot >= local.config.general.min_membership_approves:
        poll.active = False
        poll.accepted = True
        poll.creator.external = False
        local.session.add(poll)
        local.session.add(poll.creator)
        local.session.commit()

    elif -result_of_ballot >= local.config.general.min_membership_disapproves:
        poll.active = False
        poll.accepted = False
        local.session.add(poll)
        local.session.commit()

    if not poll.active:
        Callback.push(
            schemas.EventType.POLL_CLOSED,
            {"id": poll.id, "user": poll.creator_id, "accepted": poll.accepted, "aborted": False, "last_vote": model.id, "total_votes": len(ballot.votes), "result": ballot.result}
        )
    return schemas.PollVoteResponse(poll=poll.schema, vote=model.schema)


@router.post(
    "/polls/abort",
    tags=["Polls"],
    response_model=schemas.Poll,
    responses={400: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def abort_open_membership_poll(
        body: schemas.IssuerIdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an ongoing poll request (closing it without performing the transaction)

    * `400`: if the poll is unknown or already closed or if
        the issuer is not permitted to perform the operation
    """

    model = await helpers.return_one(body.id, models.Poll, local.session)
    issuer = await helpers.resolve_user_spec(body.issuer, local)

    if not model.active:
        raise BadRequest("Updating an already closed poll is not possible.", detail=str(model))
    if model.creator.id != issuer.id:
        raise BadRequest("Only the creator of a poll is allowed to abort it.", detail=str(issuer))

    model.active = False
    logger.debug(f"Aborting poll {model}")
    local.session.add(model)
    local.session.commit()

    Callback.push(
        schemas.EventType.POLL_CLOSED,
        {"id": model.id, "user": model.creator_id, "accepted": False, "aborted": True, "last_vote": None}
    )
    return model.schema
