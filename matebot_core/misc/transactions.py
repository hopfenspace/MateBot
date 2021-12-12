import logging
from typing import Optional

from sqlalchemy.orm.session import Session
from fastapi.background import BackgroundTasks

from .logger import enforce_logger
from .notifier import Callback
from ..persistence import models


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
    :raises sqlalchemy.exc.DBAPIError: in case committing to the database fails
    """

    logger = enforce_logger(logger)
    logger.info(f"Incoming transaction from {sender} to {receiver} about {amount} for {reason!r}.")

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
