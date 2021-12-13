import math
import logging
from typing import List, Optional, Tuple

from sqlalchemy.orm.session import Session
from fastapi.background import BackgroundTasks

from .logger import enforce_logger
from .notifier import Callback
from ..persistence import models


def _get_base_amount(total: int, quantities: List[int]) -> int:
    return math.ceil(total / sum(quantities))


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
    :raises ValueError: in case the amount is negative or zero
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    logger = enforce_logger(logger)
    logger.info(f"Incoming transaction from {sender} to {receiver} about {amount} for {reason!r}.")

    amount = int(amount)
    if amount <= 0:
        raise ValueError(f"Amount {amount} can't be negative or zero!")

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


def create_one_to_many_transaction(
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
        negative or the quantity of any user is negative
    :raises KeyError: in case the custom indicator string is somehow broken
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    logger = enforce_logger(logger)
    logger.info(f"Incoming 1->n transaction from {sender} to {receivers} about base {base_amount} for {reason!r}.")

    base_amount = int(base_amount)
    if base_amount <= 0:
        raise ValueError(f"Base amount {base_amount} can't be negative or zero!")

    if len(receivers) == 0:
        raise ValueError(f"No known receivers for transaction of base amount {base_amount}")
    elif len(receivers) == 1:
        logger.warning("Using 1->n transaction with n=1 instead of normal transaction!")

    # Testing the indicator before performing actual operations
    _ = indicator.format(reason="", n=0)

    if any(quantity for receiver, quantity in receivers if int(quantity) < 0):
        raise ValueError("A quantity can not be negative!")

    transactions = []
    multi = models.MultiTransaction(base_amount=base_amount)

    for i, receiver_quantity in enumerate(receivers):
        receiver, quantity = receiver_quantity
        quantity = int(quantity)
        amount = base_amount * quantity
        transactions.append(models.Transaction(
            sender_id=sender.id,
            receiver_id=receiver.id,
            amount=amount,
            reason=indicator.format(reason=reason, n=i),
            multi_transaction=multi
        ))
        sender.balance -= amount
        receiver.balance += amount
        logger.debug(f"Creating single transaction {sender.id} -> {receiver.id} of {amount}")

    session.add(sender)
    session.add_all(r for r, q in receivers)
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
    total_amount = int(total_amount)
    if total_amount <= 0:
        raise ValueError(f"Total amount {total_amount} can't be negative or zero!")
    base_amount = _get_base_amount(total_amount, [q for r, q in receivers])
    return create_one_to_many_transaction(sender, receivers, base_amount, reason, session, logger, indicator, tasks)


def create_many_to_one_transaction(
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
        negative or the quantity of any user is negative
    :raises KeyError: in case the custom indicator string is somehow broken
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    logger = enforce_logger(logger)
    logger.info(f"Incoming n->1 transaction from {senders} to {receiver} about base {base_amount} for {reason!r}.")

    base_amount = int(base_amount)
    if base_amount <= 0:
        raise ValueError(f"Base amount {base_amount} can't be negative or zero!")

    if len(senders) == 0:
        raise ValueError(f"No known senders for transaction of base amount {base_amount}")
    elif len(senders) == 1:
        logger.warning("Using n->1 transaction with n=1 instead of normal transaction!")

    # Testing the indicator before performing actual operations
    _ = indicator.format(reason="", n=0)

    if any(quantity for sender, quantity in senders if int(quantity) < 0):
        raise ValueError("A quantity can not be negative!")

    transactions = []
    multi = models.MultiTransaction(base_amount=base_amount)

    for i, sender_quantity in enumerate(senders):
        sender, quantity = sender_quantity
        quantity = int(quantity)
        amount = base_amount * quantity
        transactions.append(models.Transaction(
            sender_id=sender.id,
            receiver_id=receiver.id,
            amount=amount,
            reason=indicator.format(reason=reason, n=i),
            multi_transaction=multi
        ))
        sender.balance -= amount
        receiver.balance += amount
        logger.debug(f"Creating single transaction {sender.id} -> {receiver.id} of {amount}")

    session.add(receiver)
    session.add_all(s for s, q in senders)
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
    total_amount = int(total_amount)
    if total_amount <= 0:
        raise ValueError(f"Total amount {total_amount} can't be negative or zero!")
    base_amount = _get_base_amount(total_amount, [q for s, q in senders])
    return create_many_to_one_transaction(senders, receiver, base_amount, reason, session, logger, indicator, tasks)
