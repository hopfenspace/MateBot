"""
MateBot library to easily manage refunds
"""

import logging
from typing import Tuple

from sqlalchemy.orm.session import Session

from .logger import enforce_logger
from .notifier import Callback
from .transactions import create_transaction
from ..persistence import models
from ..schemas.events import EventType


def attempt_closing_refund(
        refund: models.Refund,
        session: Session,
        limits: Tuple[int, int],
        logger: logging.Logger
) -> bool:
    """
    Attempt to close an open refund request

    :param refund: existing model of an open refund request
    :param session: SQLAlchemy session used to perform database operations
    :param limits: tuple defining the limits for approving & disapproving a refund request
    :param logger: logger that should be used for DEBUG and WARNING messages
    :return: indicator whether the refund was closed (the refund won't be closed
        when the limit of approving or disapproving votes hasn't been reached)
    """

    logger = enforce_logger(logger)
    logger.debug(f"Checking whether refund {refund.id} should be closed...")
    logger.debug(f"Linked ballot: {str(refund.ballot)}")

    if not refund.active:
        logger.warning(f"Refund {refund.id} is already closed, it can't be attempted to be closed!")
        return False

    result_of_ballot = refund.ballot.result
    if result_of_ballot < limits[0] and -result_of_ballot < limits[1]:
        return False

    refund.active = False

    if result_of_ballot >= limits[0]:
        accepted = True
        logger.info(f"The refund {refund.id} will be accepted")
        sender = session.query(models.User).filter_by(special=True).all()[0]
        receiver = refund.creator
        refund.transaction = create_transaction(
            sender, receiver, refund.amount, refund.description, session, logger
        )
        logger.debug(f"Successfully created transaction {refund.transaction.id} for refund {refund.id}")
    else:
        accepted = False
        logger.debug(f"The refund {refund.id} will be closed without performing transactions.")

    session.add(refund)
    session.commit()
    logger.debug(f"Successfully closed refund {refund.id}")

    Callback.push(
        EventType.REFUND_CLOSED,
        {"id": refund.id, "aborted": False, "accepted": accepted, "transaction": refund.transaction_id}
    )
    return True
