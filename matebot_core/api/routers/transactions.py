"""
MateBot router module for /transactions requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import Conflict, NotFound, MissingImplementation
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
    status_code=201,
    response_model=schemas.Transaction,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}},
    description="Make a new transaction using the specified data. Note that transactions "
                "can't be edited after being sent to this endpoint by design, so take care. "
                "The frontend application might want to request explicit user approval. "
                "A 404 error will be returned if the sender or receiver users can't be "
                "determined. A 409 error will be returned if any supplied aliases are not "
                "accurate (e.g. outdated), or when the sender equals the receiver."
)
def make_a_new_transaction(
        transaction: schemas.TransactionCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    def _get_user(data, target: str) -> models.User:
        if isinstance(data, schemas.Alias):
            alias = local.session.get(models.UserAlias, data.id)
            if alias is None:
                raise NotFound(f"Alias ID {data.id!r}")
            if alias.schema != transaction.sender:
                raise Conflict(
                    "Invalid state of the user alias. Query the aliases to update.",
                    f"Expected: {alias.schema!r}; actual: {transaction.sender!r}"
                )
            user_id = alias.user_id
        elif isinstance(data, int):
            user_id = data
        else:
            raise TypeError(f"Unexpected type {type(data)} for {data!r}")

        user = local.session.get(models.User, user_id)
        if user is None:
            raise NotFound(f"User ID {user_id} as {target}")
        return user

    sender = _get_user(transaction.sender, "sender")
    receiver = _get_user(transaction.receiver, "receiver")

    logger.debug(
        f"Incoming transaction from {sender} to {receiver} "
        f"about {transaction.amount!r} for {transaction.reason!r}"
    )

    model = models.Transaction(
        sender_id=sender.id,
        receiver_id=receiver.id,
        amount=transaction.amount,
        reason=transaction.reason
    )
    sender.balance -= transaction.amount
    receiver.balance += transaction.amount
    return helpers.create_new_of_model(model, local, logger, more_models=[sender, receiver])


@router.get(
    "/{transaction_id}",
    response_model=schemas.Transaction,
    responses={404: {"model": schemas.APIError}},
    description="Return details about a specific transaction identified by its "
                "`transaction_id`. A 404 error will be returned if that ID is unknown."
)
def get_transaction_by_id(
        transaction_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    return helpers.get_one_of_model(transaction_id, models.Transaction, local)


@router.get(
    "/user/{user_id}",
    response_model=List[schemas.Transaction],
    responses={404: {"model": schemas.APIError}},
    description="Return a list of all transactions made by a specific user identified by "
                "its `user_id`. A 404 error will be returned if the user ID is unknown."
)
def get_all_transactions_of_user(user_id: pydantic.NonNegativeInt):
    raise MissingImplementation("get_all_transactions_of_user")


