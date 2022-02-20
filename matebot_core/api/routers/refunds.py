"""
MateBot router module for /refunds requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import BadRequest, Conflict, ForbiddenChange, MissingImplementation
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.refunds import close_refund
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
            poll=models.Poll(
                question=f"Accept refund request for {refund.description!r}?",
                changeable=False
            )
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
    raise MissingImplementation("vote_for_refund_request")
