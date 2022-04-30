"""
MateBot router module for /transactions requests
"""

import logging
from typing import List, Optional, Union

import pydantic
from fastapi import Depends

from ._router import router
from ..base import APIException, BadRequest, Conflict, NotFound
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.transactions import create_transaction
from ... import schemas


logger = logging.getLogger(__name__)


@router.get("/transactions", tags=["Transactions"], response_model=List[schemas.Transaction])
@versioning.versions(minimal=1)
async def search_for_transactions(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        sender_id: Optional[pydantic.NonNegativeInt] = None,
        receiver_id: Optional[pydantic.NonNegativeInt] = None,
        member_id: Optional[pydantic.NonNegativeInt] = None,
        amount: Optional[pydantic.NonNegativeInt] = None,
        reason: Optional[pydantic.constr(max_length=255)] = None,
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


@router.post(
    "/transactions/send",
    tags=["Transactions"],
    status_code=201,
    response_model=schemas.Transaction,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(minimal=1)
async def send_money_between_two_users(
        transaction: schemas.TransactionCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Make a new ordinary one-to-one transaction between two users

    Note that transactions can't be edited after being sent to this
    endpoint by design, so take care doing that. The frontend application
    might want to request explicit user approval ahead of time.

    * `400`: if the transaction is not allowed for various reasons,
        e.g. sender equals receiver, either of those users
        is disabled or is external but has no active voucher or if
        the sender's or receiver's user specification couldn't be resolved
    * `404`: if the sender or receiver user IDs are unknown
    * `409`: if the sender is the community user
    """

    sender = await helpers.resolve_user_spec(transaction.sender, local)
    receiver = await helpers.resolve_user_spec(transaction.receiver, local)
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

    return create_transaction(sender, receiver, amount, reason, local.session, logger, local.tasks).schema


@router.post(
    "/transactions/consume",
    tags=["Transactions"],
    status_code=201,
    response_model=schemas.Transaction,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(minimal=1)
async def send_money_between_two_users(
        consumption: schemas.Consumption,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Make a new consumption (user-to-community transaction)

    Note that transactions can't be edited after being sent to this
    endpoint by design, so take care doing that. The frontend application
    might want to request explicit user approval ahead of time.

    * `400`: if the consuming user is disabled or has no rights
        to consume goods (being an external user without voucher)
        or if its user specification couldn't be resolved
    * `404`: if the sender user or consumable isn't found
    * `409`: if the consuming user is the community itself or if no community
        user was found at all (meaning the DB wasn't set up properly)
    """

    community = local.session.query(models.User).filter_by(special=True).first()
    if community is None:
        raise Conflict("No community user found. Please make sure to setup the DB correctly.")

    user = await helpers.resolve_user_spec(consumption.user, local)
    if user.special:
        raise Conflict("The special community user can't consume goods.", str(user.schema))
    if not user.active:
        raise BadRequest(f"The disabled user {user.username!r} can't consume goods.", str(user.schema))
    if user.external and user.voucher_id is None:
        raise BadRequest("You can't consume any goods, since you are an external user without voucher.")

    consumables = [c for c in local.config.consumables if c.name == consumption.consumable]
    if len(consumables) == 0:
        raise NotFound(f"Consumable {consumption.consumable}")
    consumable = consumables[0]
    reason = f"consume: {consumption.amount}x {consumable.name}"
    total = consumable.price * consumption.amount
    return create_transaction(user, community, total, reason, local.session, logger, local.tasks).schema
