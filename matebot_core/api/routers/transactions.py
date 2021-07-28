"""
MateBot router module for /transactions requests
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
    prefix="/transactions",
    tags=["Transactions"]
)


@router.get(
    "",
    response_model=List[schemas.Transaction],
    description="Return a list of all transactions in the system."
)
def get_all_transactions(local: LocalRequestData = Depends(LocalRequestData)):
    return helpers.get_all_of_model(models.Transaction, local)


@router.post(
    "",
    response_model=schemas.Transaction,
    description="Make a new transaction using the specified data. Note that transactions "
                "can't be edited after being sent to this endpoint by design, so take care. "
                "The frontend application might want to introduce explicit user approval."
)
def make_a_new_transaction(transaction: schemas.IncomingTransaction):
    raise MissingImplementation("make_a_new_transaction")


@router.get(
    "/{transaction_id}",
    response_model=schemas.Transaction,
    responses={404: {}},
    description="Return details about a specific transaction identified by its "
                "`transaction_id`. A 404 error will be returned if that ID is unknown."
)
def get_transaction_by_id(
        transaction_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_transaction_by_id")


@router.get(
    "/user/{user_id}",
    response_model=List[schemas.Transaction],
    responses={404: {}},
    description="Return a list of all transactions made by a specific user identified by "
                "its `user_id`. A 404 error will be returned if the user ID is unknown."
)
def get_all_transactions_of_user(user_id: pydantic.NonNegativeInt):
    raise MissingImplementation("get_all_transactions_of_user")


@router.get(
    "/collective/{collective_id}",
    response_model=List[schemas.Transaction],
    responses={404: {}},
    description="Return a list of all transactions associated with a specific collective "
                "operation identified by the `collective_id`. The list may be empty if "
                "the collective operation was cancelled or not submitted yet. "
                "A 404 error will be returned if the collective ID is unknown."
)
def get_all_transactions_of_collective(collective_id: pydantic.NonNegativeInt):
    raise MissingImplementation("get_all_transactions_of_collective")
