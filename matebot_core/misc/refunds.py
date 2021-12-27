"""
MateBot library to easily manage refunds
"""

import logging
import datetime
from typing import Optional, Tuple

from sqlalchemy.orm.session import Session
from fastapi.background import BackgroundTasks

from .logger import enforce_logger
from .notifier import Callback
from .transactions import create_transaction
from ..persistence import models


def close_refund(
        refund: models.Refund,
        session: Session,
        limits: Tuple[int, int],
        logger: logging.Logger,
        tasks: Optional[BackgroundTasks] = None
) -> models.Refund:
    """"""

    logger = enforce_logger(logger)
    logger.debug(f"Closing refund {refund.id}: {str(refund)}")
    logger.debug(f"Linked poll: {str(refund.poll)}")

    if not refund.active:
        raise RuntimeError("Refund is not active, can't be closed")

    sum_of_votes = sum(v.vote for v in refund.poll.votes)
    min_approves = limits[0]
    min_disapproves = limits[1]
    if sum_of_votes < min_approves and -sum_of_votes < min_disapproves:
        raise ValueError(f"Not enough approving/disapproving votes for refund {refund.id}")

    refund.active = False
    refund.poll.result = sum_of_votes
    refund.poll.active = False
    refund.poll.closed = datetime.datetime.now().replace(microsecond=0)

    if sum_of_votes >= min_approves:
        logger.debug(f"The refund {refund.id} will be accepted!")
        sender = session.query(models.User).filter_by(special=True).all()[0]
        receiver = refund.creator
        refund.transaction = create_transaction(
            sender, receiver, refund.amount, refund.description, session, logger, tasks
        )

    session.add(refund)
    session.add(refund.poll)
    session.commit()
    logger.debug(f"Successfully closed refund {refund.id}")

    if tasks is not None:
        tasks.add_task(
            Callback.created,
            type(refund).__name__.lower(),
            refund.id,
            logger,
            session.query(models.Callback).all()
        )

    return refund
