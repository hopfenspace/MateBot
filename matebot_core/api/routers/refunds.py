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
from .. import helpers, notifier, versioning
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
                changable=False
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
    its associated ballot to finally calculate the result of all votes.
    If the total of approving votes fulfills the minimum limit of necessary
    approves, the refund will be accepted. All transactions related to this
    particular refund will be executed. If the total of disapproving votes
    fulfills the minimum limit of necessary disapproves, the refund will be
    rejected. However, trying to close a refund that didn't reach any of those
    two minimum number of votes in either direction won't be allowed.
    Of course, the associated ballot will always be closed when the refund it
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
    ballot = model.ballot

    if not model.active:
        if refund.active:
            logger.warning(f"Request to re-open a closed refund blocked: {model!r}")
            raise ForbiddenChange(
                "Refund.active",
                detail=f"{model!r} has already been closed, it can't be reopened again!"
            )
        if ballot.closed is None:
            logger.error(f"Inconsistent data detected: {ballot}, {refund}")
        return await helpers.get_one_of_model(refund.id, models.Refund, local)

    if refund.active:
        return await helpers.get_one_of_model(refund.id, models.Refund, local)

    sum_of_votes = sum(v.vote for v in ballot.votes)
    min_approves = local.config.general.min_refund_approves
    min_disapproves = local.config.general.min_refund_disapproves
    if sum_of_votes < min_approves and -sum_of_votes < min_disapproves:
        raise Conflict(
            repeat=True,
            message=f"Not enough approving/disapproving votes for refund {refund.id}",
            detail=f"refund={refund}, sum={sum_of_votes}, required=({min_approves}, {min_disapproves})"
        )

    model.active = False
    ballot.result = sum_of_votes
    ballot.active = False
    ballot.closed = datetime.datetime.now().replace(microsecond=0)

    if sum_of_votes >= min_approves:
        sender = await helpers.return_unique(models.User, local.session, special=True)
        receiver = model.creator
        model.transaction = await helpers.create_transaction(
            sender, receiver, model.amount, model.description, local, logger=logger
        )

    await helpers._commit(local.session, ballot, logger=logger)
    local.tasks.add_task(
        notifier.Callback.updated,
        models.Ballot.__name__.lower(),
        ballot.id,
        logger,
        await helpers.return_all(models.Callback, local.session)
    )

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA_WITH_TAG)


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
