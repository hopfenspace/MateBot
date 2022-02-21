"""
MateBot router module for /refunds requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.refunds import attempt_closing_refund
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/refunds", tags=["Refunds"])


@router.get(
    "",
    response_model=List[schemas.Refund]
)
@versioning.versions(minimal=1)
async def get_all_refunds(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known refunds.
    """

    return await helpers.get_all_of_model(models.Refund, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Refund,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def create_new_refund(
        refund: schemas.RefundCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new refund based on the specified data.

    A 404 error will be returned if the user ID of the `creator` is unknown.
    A 409 error will be returned if the special community user is the creator.
    """

    creator = await helpers.return_one(refund.creator_id, models.User, local.session)
    if creator.special:
        raise Conflict("Community user can't create a refund")
    if not creator.active:
        raise BadRequest("A disabled user can't create refund requests.", str(refund))
    if creator.external and not creator.voucher_id:
        raise BadRequest("You can't create a refund request without voucher.", str(refund))

    return await helpers.create_new_of_model(
        models.Refund(
            amount=refund.amount,
            description=refund.description,
            creator=creator,
            active=refund.active,
            ballot=models.Ballot()
        ),
        local,
        logger
    )


@router.get(
    "/{refund_id}",
    response_model=schemas.Refund,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_refund_by_id(
        refund_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return an existing refund.

    A 404 error will be returned if the specified refund ID was not found.
    """

    return await helpers.get_one_of_model(refund_id, models.Refund, local)


@router.get(
    "/creator/{user_id}",
    response_model=List[schemas.Refund],
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_refunds_by_creator(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return a list of all refunds which have been created by the specified user.

    A 404 error will be returned if the user ID is unknown.
    """

    await helpers.return_one(user_id, models.User, local.session)
    return await helpers.get_all_of_model(models.Refund, local, creator_id=user_id)


@router.post(
    "/vote",
    response_model=schemas.RefundVoteResponse,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(1)
async def vote_for_refund_request(
        vote: schemas.VoteCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Add a new vote for an open refund request

    This endpoint will take care of closing the refund request if
    enough votes for or against it have been created. The limits
    are set in the server's configuration. The newly transaction can
    be found in the refund's transaction attribute (if the refund
    request has been accepted, otherwise this attribute is null).

    A 400 error will be returned if the refund is not active anymore, the user has
    already voted in the specified ballot, the user is not active or unprivileged.
    A 404 error will be returned if the user ID or ballot ID is unknown.
    A 409 error will be returned if the voter is the community user, if an
    invalid state has been detected or the ballot referenced by the newly
    created vote is actually about a membership poll instead of a refund request.
    """

    user = await helpers.return_one(vote.user_id, models.User, local.session)
    ballot = await helpers.return_one(vote.ballot_id, models.Ballot, local.session)

    if user.special:
        raise Conflict("The community user can't vote in refund requests.")
    if ballot.polls:
        raise Conflict("This endpoint ('POST /refunds/vote') can't be used to vote on polls.")
    if not ballot.refunds:
        raise Conflict("The ballot didn't reference any refund request. Please file a bug report.", str(ballot))
    if len(ballot.refunds) != 1:
        raise Conflict("The ballot didn't reference exactly one refund request. Please file a bug report.", str(ballot))
    refund: models.Refund = ballot.refunds[0]

    if not refund.active:
        raise BadRequest("You can't vote on already closed refund requests.")
    if local.session.query(models.Vote).filter_by(ballot=ballot, user=user).all():
        raise BadRequest("You have already voted for this refund request. You can't vote twice.")
    if not user.active:
        raise BadRequest("Your user account was disabled. Therefore, you can't vote for this refund request.")
    if not user.permission:
        raise BadRequest("You are not permitted to participate in ballots about refund requests.")
    if user.id == refund.creator_id:
        raise BadRequest("You can't vote on your own refund requests.")

    model = models.Vote(user=user, ballot=ballot, vote=vote.vote)
    await helpers.create_new_of_model(model, local, logger)

    attempt_closing_refund(
        refund,
        local.session,
        (local.config.general.min_refund_approves, local.config.general.min_refund_disapproves),
        logger,
        local.tasks
    )
    return schemas.RefundVoteResponse(refund=refund.schema, vote=model.schema)


@router.post(
    "/abort/{refund_id}",
    response_model=schemas.Refund,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def abort_open_refund_request(
        refund_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an ongoing refund request (closing it without performing the transaction)

    A 400 error will be returned if the refund is already closed.
    A 404 error will be returned if the refund ID is unknown.
    """

    model = await helpers.return_one(refund_id, models.Refund, local.session)

    if not model.active:
        raise BadRequest("Updating an already closed refund is not possible.", detail=str(model))

    model.active = False
    logger.debug(f"Aborting refund {model}")
    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)
