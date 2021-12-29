"""
MateBot router module for /refunds requests
"""

import logging
import datetime
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import Conflict, ForbiddenChange
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.refunds import close_refund
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

    creator = await helpers.return_one(refund.creator, models.User, local.session)
    if creator.special:
        raise Conflict("Community user can't create a refund")

    return await helpers.create_new_of_model(
        models.Refund(
            amount=refund.amount,
            description=refund.description,
            creator=creator,
            active=refund.active,
            poll=models.Poll(
                question=f"Accept refund request for {refund.description!r}?",
                changeable=False
            )
        ),
        local,
        logger
    )


@router.put(
    "",
    response_model=schemas.Refund,
    responses={k: {"model": schemas.APIError} for k in (403, 404, 409)}
)
@versioning.versions(minimal=1)
async def close_refund_by_id(
        refund: schemas.Refund,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing refund, possibly calculating the result of all votes and
    eventually paying back money in case the refund got approved properly.

    Note that closing the refund by setting `active` to False also closes
    its associated poll to finally calculate the result of all votes.
    If the total of approving votes fulfills the minimum limit of necessary
    approves, the refund will be accepted. All transactions related to this
    particular refund will be executed. If the total of disapproving votes
    fulfills the minimum limit of necessary disapproves, the refund will be
    rejected. However, trying to close a refund that didn't reach any of those
    two minimum number of votes in either direction won't be allowed.
    Of course, the associated poll will always be closed when the refund it
    refers to gets closed, for whatever reason, in order to prevent changes.
    To abort an open refund, use `DELETE /refunds` instead of this method.

    A 403 error will be returned if any other attribute than `active` has
    been changed or if a try to re-open a refund was attempted. A 404 error
    will be returned if the refund ID is not found. A 409 error will be
    returned if the refund could not be accepted or rejected, because
    it didn't reach any of the minimum limits for particular actions.
    """

    model = await helpers.return_one(refund.id, models.Refund, local.session)
    helpers.restrict_updates(refund, model.schema)
    poll = model.poll

    if not model.active:
        if refund.active:
            logger.warning(f"Request to re-open a closed refund blocked: {model!r}")
            raise ForbiddenChange(
                "Refund.active",
                detail=f"{model!r} has already been closed, it can't be reopened again!"
            )
        if poll.closed is None:
            logger.error(f"Inconsistent data detected: {poll}, {refund}")
        return await helpers.get_one_of_model(refund.id, models.Refund, local)

    if refund.active:
        return await helpers.get_one_of_model(refund.id, models.Refund, local)

    sum_of_votes = sum(v.vote for v in poll.votes)
    min_approves = local.config.general.min_refund_approves
    min_disapproves = local.config.general.min_refund_disapproves
    if sum_of_votes < min_approves and -sum_of_votes < min_disapproves:
        raise Conflict(
            repeat=True,
            message=f"Not enough approving/disapproving votes for refund {refund.id}",
            detail=f"refund={refund}, sum={sum_of_votes}, required=({min_approves}, {min_disapproves})"
        )

    return close_refund(model, local.session, (min_approves, min_disapproves), logger, local.tasks).schema


@router.delete(
    "",
    status_code=204,
    responses={k: {"model": schemas.APIError} for k in (403, 404, 409, 412)}
)
@versioning.versions(minimal=1)
async def abort_open_refund(
        refund: schemas.Refund,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an open refund request without performing any transactions,
    discarding the poll or votes. However, the refund object will be deleted.

    A 403 error will be returned if the refund was already closed.
    A 404 error will be returned if the requested `id` doesn't exist.
    A 409 error will be returned if the object is not up-to-date, which
    means that the user agent needs to get the object before proceeding.
    A 412 error will be returned if the conditional request fails.
    """

    def hook(model, *_):
        if not model.active:
            raise ForbiddenChange("Refund", str(refund))

        model.poll.result = 0
        model.poll.active = False
        model.poll.closed = datetime.datetime.now().replace(microsecond=0)
        local.session.add(model.poll)

    return await helpers.delete_one_of_model(
        refund.id,
        models.Refund,
        local,
        schema=refund,
        logger=logger,
        hook_func=hook
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
