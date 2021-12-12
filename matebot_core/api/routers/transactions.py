"""
MateBot router module for /transactions requests
"""

import logging
from typing import List, Union

import pydantic
from fastapi import APIRouter, Depends

from ..base import APIException, Conflict, NotFound
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.transactions import create_transaction
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/transactions",
    tags=["Transactions"]
)


@router.get(
    "",
    response_model=List[schemas.Transaction]
)
@versioning.versions(minimal=1)
async def get_all_transactions(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all transactions in the system.
    """

    return await helpers.get_all_of_model(models.Transaction, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Transaction,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(minimal=1)
async def make_a_new_transaction(
        transaction: Union[schemas.TransactionCreation, schemas.Consumption],
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Make a new transaction using the specified data and return it.

    Note that transactions can't be edited after being sent to this
    endpoint by design, so take care doing that. The frontend application
    might want to request explicit user approval ahead of time.

    This endpoint allows both one-to-one and consumption transactions.
    A one-to-one transaction is the simplest form, where one user sends
    money to another user. The latter form lets a user consume goods
    (which are in stock, ideally), so they will be paid to the community.

    Specific information about one-to-one transactions:

    A 404 error will be returned if the sender or receiver users can't be
    determined. A 409 error will be returned if any supplied aliases are not
    accurate (e.g. outdated), or when the sender equals the receiver.

    Specific information about consumption transactions:

    Using `adjust_stock=true` will be ignored when `respect_stock` is `false`.
    Note that its the client's duty to select the appropriate response to
    the successful consumption, since one consumable type may have any number
    of consumable messages which may be used as a reply template to the user.

    A 400 error will be returned when the specified user who should consume
    the good is the special community user. A 404 error will be returned
    if the sender user or consumable isn't found. A 409 error will be returned
    when the good is out of stock (this is already the case when there's
    not enough available to fit the needs, e.g. requesting four items
    where only two items are in stock would lead to such an error).
    """

    if isinstance(transaction, schemas.Consumption):
        consumption = transaction

        user = await helpers.return_one(consumption.user, models.User, local.session)
        consumable: models.Consumable = await helpers.return_one(
            consumption.consumable_id,
            models.Consumable,
            local.session
        )

        if user.special:
            raise APIException(
                status_code=400,
                message="The special community user can't consume goods.",
                detail=str(user.schema)
            )

        wastage = 0
        if consumption.respect_stock:
            if consumable.stock < consumption.amount:
                raise Conflict(
                    f"Not enough {consumable.name} in stock to consume the goods.",
                    f"requested={consumption.amount}, stock={consumable.stock}",
                    repeat=True
                )
            if consumption.adjust_stock:
                wastage = consumption.amount

        community = await helpers.return_unique(models.User, local.session, special=True)

        reason = f"consume: {consumption.amount}x {consumable.name}"
        total = consumable.price * consumption.amount
        consumable.stock -= wastage
        t = create_transaction(user, community, total, reason, local.session, logger, local.tasks)
        return await helpers.get_one_of_model(t.id, models.Transaction, local)

    elif not isinstance(transaction, schemas.TransactionCreation):
        raise APIException(status_code=500, detail="Invalid input data validation", repeat=False)

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

        found_user = local.session.get(models.User, user_id)
        if found_user is None:
            raise NotFound(f"User ID {user_id} as {target}")
        return found_user

    sender = _get_user(transaction.sender, "sender")
    receiver = _get_user(transaction.receiver, "receiver")
    amount = transaction.amount
    reason = transaction.reason

    t = create_transaction(sender, receiver, amount, reason, local.session, logger, local.tasks)
    return await helpers.get_one_of_model(t.id, models.Transaction, local)


@router.get(
    "/{transaction_id}",
    response_model=schemas.Transaction,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_transaction_by_id(
        transaction_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return details about a specific transaction identified by its transaction ID.

    A 404 error will be returned if the `transaction_id` is unknown.
    """

    return await helpers.get_one_of_model(transaction_id, models.Transaction, local)


@router.get(
    "/sender/{user_id}",
    response_model=List[schemas.Transaction],
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_all_transactions_of_sender(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return a list of all transactions sent by a specific user identified by its user ID.

    A 404 error will be returned if the user ID is unknown.
    """

    user = await helpers.return_one(user_id, models.User, local.session)
    return await helpers.get_all_of_model(models.Transaction, local, sender=user)


@router.get(
    "/receiver/{user_id}",
    response_model=List[schemas.Transaction],
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_all_transactions_of_receiver(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return a list of all transactions received by a specific user identified by its user ID.

    A 404 error will be returned if the user ID is unknown.
    """

    user = await helpers.return_one(user_id, models.User, local.session)
    return await helpers.get_all_of_model(models.Transaction, local, receiver=user)
