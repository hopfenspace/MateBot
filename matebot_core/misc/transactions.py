"""
MateBot library to easily create new transactions of various types
"""

import enum
import math
import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm.session import Session
from fastapi.background import BackgroundTasks

from .logger import enforce_logger
from .notifier import Callback
from ..persistence import models


class _SimpleMultiTransactionMode(enum.Enum):
    ONE_TO_MANY = "1->n"
    MANY_TO_ONE = "n->1"


class _SimpleMultiTransactionAmount(enum.Enum):
    BASE = "base"
    TOTAL = "total"


def create_transaction(
        sender: models.User,
        receiver: models.User,
        amount: int,
        reason: str,
        session: Session,
        logger: logging.Logger,
        tasks: Optional[BackgroundTasks] = None
) -> models.Transaction:
    """
    Send the specified amount of money from one user to another one

    :param sender: user that sends money (whose balance will be decreased by amount)
    :param receiver: user that receives money (whose balance will be increased by amount)
    :param amount: amount of money to be transferred between the two parties
    :param reason: textual description of the transaction
    :param session: SQLAlchemy session used to perform database operations
    :param logger: logger that should be used for INFO and ERROR messages
    :param tasks: FastAPI's list of background tasks the callback task should be added to
        (use None to disable creating the notification background task completely)
    :return: the newly created and committed Transaction object
    :raises ValueError: in case the amount is not positive or some user ID is not set
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    logger = enforce_logger(logger)
    logger.info(f"Incoming transaction from {sender} to {receiver} about {amount} for {reason!r}.")

    amount = int(amount)
    if amount <= 0:
        raise ValueError(f"Amount {amount} can't be negative or zero!")

    if sender.id is None or receiver.id is None:
        raise ValueError("ID of some user None!")

    model = models.Transaction(
        sender_id=sender.id,
        receiver_id=receiver.id,
        amount=amount,
        reason=reason
    )
    sender.balance -= amount
    receiver.balance += amount

    session.add(sender)
    session.add(receiver)
    session.add(model)
    session.commit()
    logger.debug(f"Successfully committed new transaction {model.id}")

    if tasks is not None:
        tasks.add_task(
            Callback.created,
            type(model).__name__.lower(),
            model.id,
            logger,
            session.query(models.Callback).all()
        )

    return model


def _make_simple_multi_transaction(
        sender: models.User,
        receivers_uncompressed: List[Tuple[models.User, int]],
        pre_amount: int,
        amount_type: _SimpleMultiTransactionAmount,
        reason: str,
        session: Session,
        logger: logging.Logger,
        direction: _SimpleMultiTransactionMode,
        indicator: Optional[str] = None,
        tasks: Optional[BackgroundTasks] = None
) -> Tuple[models.MultiTransaction, List[models.Transaction]]:
    """
    Perform a simple multi transaction; see the other `create_*` functions for its API
    """

    logger = enforce_logger(logger)
    logger.debug(
        f"Incoming simple multi transaction {direction.name} about "
        f"{pre_amount} ({amount_type.name}) for {reason!r}"
    )

    if amount_type == _SimpleMultiTransactionAmount.TOTAL:
        total_amount = int(pre_amount)
        if total_amount <= 0:
            raise ValueError(f"Total amount {total_amount} can't be negative or zero!")
        quantities = sum(q for _, q in receivers_uncompressed)
        if quantities == 0:
            raise ValueError(f"No participants with quantity > 1 given!")
        base_amount = math.ceil(total_amount / quantities)
    elif amount_type == _SimpleMultiTransactionAmount.BASE:
        base_amount = int(pre_amount)
    else:
        raise TypeError(f"Unknown enum {amount_type}")

    if base_amount <= 0 or int(base_amount) <= 0:
        raise ValueError(f"Base amount {base_amount} can't be negative or zero!")

    if sender.id is None or any(receiver for receiver, _ in receivers_uncompressed if receiver.id is None):
        raise ValueError("The user ID of some user is None!")
    if len(receivers_uncompressed) == 0:
        raise ValueError(f"No known participants for transaction of base amount {base_amount}")

    if indicator:
        _ = indicator.format(reason="", n=0)

    if any(quantity for _, quantity in receivers_uncompressed if int(quantity) < 0):
        raise ValueError("A quantity can not be negative!")
    if len(receivers_uncompressed) == 1:
        logger.warning(f"Using {direction.value} transaction with n=1 instead of normal transaction!")

    transactions = []
    multi = models.MultiTransaction(base_amount=base_amount)

    receiver_users = {}
    receiver_count = {}
    for receiver, quantity in receivers_uncompressed:
        if receiver not in receiver_users:
            receiver_users[receiver.id] = receiver
            receiver_count[receiver.id] = 0
        receiver_count[receiver.id] += int(quantity)

    c = 0
    for user_id in receiver_users:
        if sender.id == user_id:
            continue
        c += 1
        quantity = int(receiver_count[user_id])
        amount = base_amount * quantity

        if direction == _SimpleMultiTransactionMode.ONE_TO_MANY:
            transactions.append(models.Transaction(
                sender_id=sender.id,
                receiver_id=user_id,
                amount=amount,
                reason=indicator.format(reason=reason, n=c) if indicator else reason,
                multi_transaction=multi
            ))
            sender.balance -= amount
            receiver_users[user_id].balance += amount
            logger.debug(f"Creating single transaction {sender.id} -> {user_id} of {amount}")

        elif direction == _SimpleMultiTransactionMode.MANY_TO_ONE:
            transactions.append(models.Transaction(
                sender_id=user_id,
                receiver_id=sender.id,
                amount=amount,
                reason=indicator.format(reason=reason, n=c) if indicator else reason,
                multi_transaction=multi
            ))
            receiver_users[user_id].balance -= amount
            sender.balance += amount
            logger.debug(f"Creating single transaction {user_id} -> {sender.id} of {amount}")

    session.add(sender)
    session.add_all(list(receiver_users.values()))
    session.add_all(transactions)
    session.add(multi)
    session.commit()
    logger.debug(
        f"Successfully committed new multi transaction {multi.id} and "
        f"transactions: {[t.id for t in transactions]}"
    )

    if tasks is not None:
        tasks.add_task(
            Callback.created,
            type(multi).__name__.lower(),
            multi.id,
            logger,
            session.query(models.Callback).all()
        )

    return multi, transactions


def create_one_to_many_transaction_by_base(
        sender: models.User,
        receivers: List[Tuple[models.User, int]],
        base_amount: int,
        reason: str,
        session: Session,
        logger: logging.Logger,
        indicator: Optional[str] = None,
        tasks: Optional[BackgroundTasks] = None
) -> Tuple[models.MultiTransaction, List[models.Transaction]]:
    """
    Send money from one user to a list of receiver users

    Note that the total amount of transferred money is much higher than the specified base
    amount. The actual money that one receiver gets from the sender is `base * quantity`,
    where `quantity` is the second element of the tuple (one receiver record).

    Specifying the same user multiple times in the list of receivers will not result
    in multiple transactions, but one combined transaction instead. Specifying the
    sender in the list of receivers has no effect, since the record will be ignored.
    Specifying a negative quantity or amount raises ValueErrors, zero will just be ignored.

    :param sender: user that sends the money to the receivers
    :param receivers: list of users that receive money, represented as list of tuples
        of users and their quantities (so that some users may get more money than others)
    :param base_amount: base amount of money to be transferred to a receiver with quantity=1
    :param reason: textual description of every single transaction
    :param session: SQLAlchemy session used to perform database operations
    :param logger: logger that should be used for INFO and ERROR messages
    :param indicator: optional format string that transforms the reason before creating the
        transaction to allow customization with the two possible keys being `reason` and `n`
    :param tasks: FastAPI's list of background tasks the callback task should be added to
        (use None to disable creating the notification background task completely)
    :return: both the newly created and committed MultiTransaction
        object and the list of new transactions
    :raises ValueError: in case no receivers have been given, the amount is
        negative, the quantity of any user is negative or any user has no ID
    :raises KeyError: in case the custom indicator string is somehow broken
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    return _make_simple_multi_transaction(
        sender,
        receivers,
        base_amount,
        _SimpleMultiTransactionAmount.BASE,
        reason,
        session,
        logger,
        _SimpleMultiTransactionMode.ONE_TO_MANY,
        indicator,
        tasks
    )


def create_one_to_many_transaction_by_total(
        sender: models.User,
        receivers: List[Tuple[models.User, int]],
        total_amount: int,
        reason: str,
        session: Session,
        logger: logging.Logger,
        indicator: Optional[str] = None,
        tasks: Optional[BackgroundTasks] = None
) -> Tuple[models.MultiTransaction, List[models.Transaction]]:
    """
    Send money from one user to a list of receiver users

    Note that the total amount of transferred money may be a little bit higher than the
    specified total amount, since the base amount will be evaluated as the smallest common
    amount of money for a receiver with quantity=1. Therefore, for example, if you want
    to send a total of 8 to two receivers A (quantity 2) and B (quantity 1), then the
    base amount will be 3, to make it even for all receivers. At the end, a total of
    9 will be transferred from the sender, whereof A gets 6 and B gets 3.

    Specifying the same user multiple times in the list of receivers will not result
    in multiple transactions, but one combined transaction instead. Specifying the
    sender in the list of receivers has no effect, since the record will be ignored.
    Specifying a negative quantity or amount raises ValueErrors, zero will just be ignored.

    :param sender: user that sends the money to the receivers
    :param receivers: list of users that receive money, represented as list of tuples
        of users and their quantities (so that some users may get more money than others)
    :param total_amount: minimal total amount of money to be transferred to all receivers
    :param reason: textual description of every single transaction
    :param session: SQLAlchemy session used to perform database operations
    :param logger: logger that should be used for INFO and ERROR messages
    :param indicator: optional format string that transforms the reason before creating the
        transaction to allow customization with the two possible keys being `reason` and `n`
    :param tasks: FastAPI's list of background tasks the callback task should be added to
        (use None to disable creating the notification background task completely)
    :return: both the newly created and committed MultiTransaction
        object and the list of new transactions
    :raises ValueError: in case no receivers have been given, the amount is
        negative, the quantity of any user is negative or any user has no ID
    :raises KeyError: in case the custom indicator string is somehow broken
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    return _make_simple_multi_transaction(
        sender,
        receivers,
        total_amount,
        _SimpleMultiTransactionAmount.TOTAL,
        reason,
        session,
        logger,
        _SimpleMultiTransactionMode.ONE_TO_MANY,
        indicator,
        tasks
    )


def create_many_to_one_transaction_by_base(
        senders: List[Tuple[models.User, int]],
        receiver: models.User,
        base_amount: int,
        reason: str,
        session: Session,
        logger: logging.Logger,
        indicator: Optional[str] = None,
        tasks: Optional[BackgroundTasks] = None
) -> Tuple[models.MultiTransaction, List[models.Transaction]]:
    """
    Send money from a list of users to a single users

    Note that the total amount of transferred money is much higher than the specified base
    amount. The actual money that the receiver gets from one sender is `base * quantity`,
    where `quantity` is the second element of the tuple (one sender record).

    Specifying the same user multiple times in the list of senders will not result
    in multiple transactions, but one combined transaction instead. Specifying the
    receiver in the list of senders has no effect, since the record will be ignored.
    Specifying a negative quantity or amount raises ValueErrors, zero will just be ignored.

    :param senders: list of users that send money, represented as list of tuples
        of users and their quantities (so that some users may send more money than others)
    :param receiver: user that receives the money from the senders
    :param base_amount: base amount of money to be transferred from a sender with quantity=1
    :param reason: textual description of every single transaction
    :param session: SQLAlchemy session used to perform database operations
    :param logger: logger that should be used for INFO and ERROR messages
    :param indicator: optional format string that transforms the reason before creating the
        transaction to allow customization with the two possible keys being `reason` and `n`
    :param tasks: FastAPI's list of background tasks the callback task should be added to
        (use None to disable creating the notification background task completely)
    :return: both the newly created and committed MultiTransaction
        object and the list of new transactions
    :raises ValueError: in case no senders have been given, the amount is
        negative, the quantity of any user is negative or any user has no ID
    :raises KeyError: in case the custom indicator string is somehow broken
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    return _make_simple_multi_transaction(
        receiver,
        senders,
        base_amount,
        _SimpleMultiTransactionAmount.BASE,
        reason,
        session,
        logger,
        _SimpleMultiTransactionMode.MANY_TO_ONE,
        indicator,
        tasks
    )


def create_many_to_one_transaction_by_total(
        senders: List[Tuple[models.User, int]],
        receiver: models.User,
        total_amount: int,
        reason: str,
        session: Session,
        logger: logging.Logger,
        indicator: Optional[str] = None,
        tasks: Optional[BackgroundTasks] = None
) -> Tuple[models.MultiTransaction, List[models.Transaction]]:
    """
    Send money from a list of users to a single users

    Note that the total amount of transferred money may be a little bit higher than the
    specified total amount, since the base amount will be evaluated as the smallest common
    amount of money for a sender with quantity=1. Therefore, for example, if you want
    to send a total of 8 from two senders A (quantity 2) and B (quantity 1), then the
    base amount will be 3, to make it even for all senders. At the end, a total of
    9 will be transferred to the receiver, whereof A sends 6 and B sends 3.

    Specifying the same user multiple times in the list of senders will not result
    in multiple transactions, but one combined transaction instead. Specifying the
    receiver in the list of senders has no effect, since the record will be ignored.
    Specifying a negative quantity or amount raises ValueErrors, zero will just be ignored.

    :param senders: list of users that send money, represented as list of tuples
        of users and their quantities (so that some users may send more money than others)
    :param receiver: user that receives the money from the senders
    :param total_amount: minimal total amount of money to be transferred from all senders
    :param reason: textual description of every single transaction
    :param session: SQLAlchemy session used to perform database operations
    :param logger: logger that should be used for INFO and ERROR messages
    :param indicator: optional format string that transforms the reason before creating the
        transaction to allow customization with the two possible keys being `reason` and `n`
    :param tasks: FastAPI's list of background tasks the callback task should be added to
        (use None to disable creating the notification background task completely)
    :return: both the newly created and committed MultiTransaction
        object and the list of new transactions
    :raises ValueError: in case no senders have been given, the amount is
        negative, the quantity of any user is negative or any user has no ID
    :raises KeyError: in case the custom indicator string is somehow broken
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    return _make_simple_multi_transaction(
        receiver,
        senders,
        total_amount,
        _SimpleMultiTransactionAmount.TOTAL,
        reason,
        session,
        logger,
        _SimpleMultiTransactionMode.MANY_TO_ONE,
        indicator,
        tasks
    )
