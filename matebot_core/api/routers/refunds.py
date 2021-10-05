"""
MateBot router module for /refunds requests
"""

import logging
import datetime
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import APIException, MissingImplementation
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/refunds",
    tags=["Refunds"]
)


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
    response_model=schemas.Refund,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def create_new_refund(
        refund: schemas.RefundCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new refund based on the specified data.

    A 404 error will be returned if the user ID of the `creator` is unknown.
    """

    creator = await helpers.return_one(refund.creator, models.User, local.session)
    return await helpers.create_new_of_model(
        models.Refund(
            amount=refund.amount,
            description=refund.description,
            creator=creator,
            active=refund.active,
            ballot=models.Ballot(
                question=f"Accept refund request for {refund.description!r}?",
                restricted=True
            )
        ),
        local,
        logger
    )


@router.patch(
    "",
    response_model=schemas.Refund,
    responses={403: {"model": schemas.APIError}, 404: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def close_refund_by_id(
        refund: schemas.RefundPatch,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Close a refund, calculate the result of all votes and eventually pay back money.

    If the refund or its ballot has already been closed, this
    operation will do nothing and silently return the therefore
    unmodified model. Note that closing the refund also closes its
    associated ballot to finally calculate the result of all votes.
    As transactions can't be edited after being created by design,
    it doesn't matter if a user agent calls this endpoint once or a
    thousand times. Note that the field `cancelled` can be set to
    true in order to cancel the refund and therefore prevent any
    further transactions based on this refund. Of course, the
    ballot will be closed in order to prevent changes, too. However,
    setting the field `cancelled` to false will perform the actual
    refund operation (and does a transaction), if enough votes
    approve the refund request (see list of error codes below).

    A 403 error will be returned if the refund should be accepted
    but has not enough approving votes yet (it won't be performed).
    A 404 error will be returned if the refund ID is not found.
    """

    obj = await helpers.return_one(refund.id, models.Refund, local.session)
    ballot = obj.ballot
    if ballot.closed is not None and not obj.active:
        return await helpers.get_one_of_model(refund.id, models.Refund, local)

    sum_of_votes = sum(v.vote for v in ballot.votes)
    required_votes = local.config.general.min_refund_approves
    if sum_of_votes < required_votes:
        raise APIException(
            status_code=403,
            message=f"Not enough approving votes for refund {refund.id}",
            detail=f"refund={refund}, sum={sum_of_votes}, required={required_votes}"
        )

    if ballot.closed is None and not obj.active:
        logger.error(f"Inconsistent data detected: {ballot}, {refund}")

    obj.active = False
    ballot.result = sum_of_votes
    ballot.active = False
    ballot.closed = datetime.datetime.now().replace(microsecond=0)

    # TODO: implement actual money transfer, confirmation and database commit

    raise MissingImplementation("close_refund_by_id")


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
