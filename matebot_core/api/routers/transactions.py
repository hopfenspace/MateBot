"""
MateBot router module for /transactions requests
"""

import logging
from typing import List, Optional, Union

import pydantic
from fastapi import APIRouter, Depends

from ..base import APIException, BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.transactions import create_transaction
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/transactions", tags=["Transactions"])


@router.get(
    "",
    response_model=List[schemas.Transaction]
)
@versioning.versions(minimal=1)
async def get_all_transactions(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        sender_id: Optional[pydantic.NonNegativeInt] = None,
        receiver_id: Optional[pydantic.NonNegativeInt] = None,
        member_id: Optional[pydantic.NonNegativeInt] = None,
        amount: Optional[pydantic.NonNegativeInt] = None,
        reason: Optional[pydantic.NonNegativeInt] = None,
        has_multi_transaction: Optional[bool] = None,
        multi_transaction_id: Optional[pydantic.NonNegativeInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all transactions that fulfill *all* constraints given as query parameters
    """

    def extended_filter(transaction: models.Transaction) -> bool:
        if member_id is not None and member_id not in (transaction.sender_id, transaction.receiver_id):
            return False
        if has_multi_transaction is not None and (transaction.multi_transaction_id is None) == has_multi_transaction:
            return False
        if multi_transaction_id is not None and transaction.multi_transaction_id != multi_transaction_id:
            return False
        return True

    return helpers.search_models(
        models.Transaction,
        local,
        specialized_item_filter=extended_filter,
        id=id,
        sender_id=sender_id,
        receiver_id=receiver_id,
        amount=amount,
        reason=reason
    )


@router.get(
    "/multi",
    response_model=List[schemas.MultiTransaction]
)
@versioning.versions(1)
async def search_for_multi_transactions(
        multi_transaction_id: Optional[pydantic.NonNegativeInt] = None,
        multi_transaction_base_amount: Optional[pydantic.NonNegativeInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all multi transactions that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.MultiTransaction,
        local,
        id=multi_transaction_id,
        base_amount=multi_transaction_base_amount
    )


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

        user = await helpers.return_one(consumption.user_id, models.User, local.session)
        if user.special:
            raise Conflict("The special community user can't consume goods.", str(user.schema))
        if not user.active:
            raise Conflict(f"User {user.nameusername!r} can't consume goods.", str(user.schema))
        if user.external and user.voucher_id is None:
            raise BadRequest("You can't consume any goods, since you are an external user without voucher.")
        consumable: models.Consumable = await helpers.return_one(
            consumption.consumable_id,
            models.Consumable,
            local.session
        )

        wastage = 0
        if consumption.respect_stock:
            if consumable.stock < consumption.amount:
                raise BadRequest(
                    f"Not enough {consumable.name} in stock to consume the goods.",
                    f"requested={consumption.amount}, stock={consumable.stock}",
                )
            if consumption.adjust_stock:
                wastage = consumption.amount

        community = await helpers.return_unique(models.User, local.session, special=True)

        reason = f"consume: {consumption.amount}x {consumable.name}"
        total = consumable.price * consumption.amount
        consumable.stock -= wastage
        local.session.add(consumable)
        t = create_transaction(user, community, total, reason, local.session, logger, local.tasks)
        return await helpers.get_one_of_model(t.id, models.Transaction, local)

    elif not isinstance(transaction, schemas.TransactionCreation):
        raise APIException(status_code=500, detail="Invalid input data validation", repeat=False)

    sender = await helpers.return_one(transaction.sender_id, models.User, local.session)
    receiver = await helpers.return_one(transaction.receiver_id, models.User, local.session)
    amount = transaction.amount
    reason = transaction.reason

    if sender.id == receiver.id:
        raise BadRequest("You can't send money to yourself.", str(transaction))
    if not sender.active:
        raise BadRequest(f"Disabled user {sender.username!r} can't make transactions", str(sender))
    if not receiver.active:
        raise BadRequest(f"Disabled user {receiver.username!r} can't get transactions", str(receiver))
    if sender.special:
        raise Conflict("The community mustn't send money to other users directly; use refunds instead!", str(sender))
    if sender.external and sender.voucher_id is None:
        raise BadRequest("You can't send money to others, since you are an external user without voucher.", str(sender))
    if receiver.external and receiver.voucher_id is None:
        raise BadRequest(
            f"You can't send money to {receiver.username}, since nobody vouches for {receiver.username}.",
            str(receiver)
        )

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
    "/user/{user_id}",
    response_model=List[schemas.Transaction],
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_all_transactions_of_user(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return a list of all transactions sent & received by a specific user identified by its user ID.

    A 404 error will be returned if the user ID is unknown.
    """

    await helpers.return_one(user_id, models.User, local.session)
    flt = (models.Transaction.sender_id == user_id) | (models.Transaction.receiver_id == user_id)
    return [obj.schema for obj in local.session.query(models.Transaction).filter(flt).all()]


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
