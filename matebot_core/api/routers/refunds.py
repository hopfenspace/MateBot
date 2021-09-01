"""
MateBot router module for /refunds requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from .. import helpers
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
async def create_new_refund(
        refund: schemas.RefundCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new refund based on the specified data.

    A 404 error will be returned if the user ID of the `creator` is unknown.
    """

    raise MissingImplementation("create_new_refund")


@router.patch(
    "",
    response_model=schemas.Refund,
    responses={404: {"model": schemas.APIError}}
)
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
    ballot will be closed in order to prevent changes, too.

    A 404 error will be returned if the refund ID is not found.
    """

    raise MissingImplementation("close_refund_by_id")


@router.get(
    "/{refund_id}",
    response_model=schemas.Refund,
    responses={404: {"model": schemas.APIError}}
)
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
async def get_refunds_by_creator(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return a list of all refunds which have been created by the specified user.

    A 404 error will be returned if the user ID is unknown.
    """

    raise MissingImplementation("get_refunds_by_creator")
