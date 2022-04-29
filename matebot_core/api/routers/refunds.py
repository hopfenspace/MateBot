"""
MateBot router module for /refunds requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import Depends

from ._router import router
from ..base import BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.refunds import attempt_closing_refund
from ... import schemas


logger = logging.getLogger(__name__)


@router.get("/refunds", tags=["Refunds"], response_model=List[schemas.Refund])
@versioning.versions(minimal=1)
async def search_for_refunds(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        amount: Optional[pydantic.PositiveInt] = None,
        description: Optional[pydantic.constr(max_length=255)] = None,
        active: Optional[bool] = None,
        creator_id: Optional[pydantic.NonNegativeInt] = None,
        ballot_id: Optional[pydantic.NonNegativeInt] = None,
        transaction_id: Optional[pydantic.NonNegativeInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all refunds that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.Refund,
        local,
        id=id,
        amount=amount,
        description=description,
        active=active,
        creator_id=creator_id,
        ballot_id=ballot_id,
        transaction_id=transaction_id
    )


@router.post(
    "/refunds",
    tags=["Refunds"],
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

    * `400`: if the creator is an external user without voucher or disabled
    * `404`: if the user ID of the creator is unknown
    * `409`: if the special community user is the creator
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


@router.post(
    "/refunds/vote",
    tags=["Refunds"],
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

    * `400`: if the refund is not active anymore, the user has already voted
        in the specified ballot, the user is not active or unprivileged
    * `404`: if the user ID or ballot ID is unknown.
    * `409`: if the voter is the community user, an invalid state has
        been detected or the ballot referenced by the newly created vote
        is actually about a membership poll instead of a refund request
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
    "/refunds/abort",
    tags=["Refunds"],
    response_model=schemas.Refund,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def abort_open_refund_request(
        body: schemas.IdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an ongoing refund request (closing it without performing the transaction)

    * `400`: if the refund is already closed
    * `404`: if the refund ID is unknown
    """

    model = await helpers.return_one(body.id, models.Refund, local.session)

    if not model.active:
        raise BadRequest("Updating an already closed refund is not possible.", detail=str(model))

    model.active = False
    logger.debug(f"Aborting refund {model}")
    return await helpers.update_model(model, local, logger)
