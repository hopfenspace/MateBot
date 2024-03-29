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
from ...misc.notifier import Callback
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
        limit: Optional[pydantic.NonNegativeInt] = None,
        page: Optional[pydantic.NonNegativeInt] = None,
        descending: Optional[bool] = False,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all refunds that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.Refund,
        local,
        limit=limit,
        page=page,
        descending=descending,
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
    responses={400: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def create_new_refund(
        refund: schemas.RefundCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new refund based on the specified data.

    * `400`: if the creator is an external user without voucher or disabled
        or if the creator user specification couldn't be resolved
    * `409`: if the special community user is the creator
    """

    creator = await helpers.resolve_user_spec(refund.creator, local)
    if creator.special:
        raise Conflict("The community user can't create a refund.")
    if not creator.active:
        raise BadRequest("This user account has been disabled and therefore can't create refund requests.")
    if creator.external and not creator.voucher_id:
        raise BadRequest("You can't create a refund request as external user without voucher.")

    model = models.Refund(
        amount=refund.amount,
        description=refund.description if refund.description.startswith("refund:") else f"refund: {refund.description}",
        creator=creator,
        active=True,
        ballot=models.Ballot()
    )
    local.session.add(model)
    local.session.commit()

    Callback.push(
        schemas.EventType.REFUND_CREATED,
        {"id": model.id, "user": model.creator_id, "amount": model.amount}
    )
    return model.schema


@router.post(
    "/refunds/vote",
    tags=["Refunds"],
    response_model=schemas.RefundVoteResponse,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
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
        in the specified ballot, the ballot wasn't found, the user is not active
        or unprivileged or if the voter's user specification couldn't be resolved
    * `409`: if the voter is the community user, an invalid state has
        been detected or the ballot referenced by the newly created vote
        is actually about a membership poll instead of a refund request
    """

    user = await helpers.resolve_user_spec(vote.user, local)
    ballot = await helpers.return_one(vote.ballot_id, models.Ballot, local.session)

    if user.special:
        raise Conflict("The community user can't vote in refund requests.")
    if ballot.polls:
        raise Conflict("This endpoint can't be used to vote on polls.", "Try 'POST /polls/vote' instead!")
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
        raise BadRequest("This user account has been disabled. Therefore, you can't vote for this refund request.")
    if not user.permission:
        raise BadRequest("You are not permitted to participate in ballots about refund requests.")
    if user.id == refund.creator_id:
        raise BadRequest("You can't vote on your own refund requests.")

    model = models.Vote(user=user, ballot=ballot, vote=vote.vote)
    local.session.add(model)
    local.session.commit()
    Callback.push(
        schemas.EventType.REFUND_UPDATED,
        {"id": refund.id, "last_vote": model.id, "current_result": ballot.result}
    )

    attempt_closing_refund(
        refund,
        local.session,
        (local.config.general.min_refund_approves, local.config.general.min_refund_disapproves),
        logger
    )
    return schemas.RefundVoteResponse(refund=refund.schema, vote=model.schema)


@router.post(
    "/refunds/abort",
    tags=["Refunds"],
    response_model=schemas.Refund,
    responses={400: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def abort_open_refund_request(
        body: schemas.IssuerIdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an ongoing refund request (closing it without performing the transaction)

    * `400`: if the refund is unknown or already closed or if
        the issuer is not permitted to perform the operation
    """

    model = await helpers.return_one(body.id, models.Refund, local.session)
    issuer = await helpers.resolve_user_spec(body.issuer, local)

    if not model.active:
        raise BadRequest("Updating an already closed refund is not possible.", detail=str(model))
    if model.creator.id != issuer.id:
        raise BadRequest("Only the creator of a refund is allowed to abort it.", detail=str(issuer))

    model.active = False
    logger.debug(f"Aborting refund {model}")
    local.session.add(model)
    local.session.commit()

    Callback.push(
        schemas.EventType.REFUND_CLOSED,
        {"id": model.id, "aborted": True, "accepted": False, "transaction": None}
    )
    return model.schema
