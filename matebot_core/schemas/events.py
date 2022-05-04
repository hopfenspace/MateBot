"""
MateBot schemas for the event publishing system

This module contains a schema for the event model as
well as an enum of the different known event types.
"""

import enum

import pydantic


@enum.unique
class EventType(str, enum.Enum):
    SERVER_STARTED = "server_started"
    ALIAS_CONFIRMATION_REQUESTED = "alias_confirmation_requested"
    ALIAS_CONFIRMED = "alias_confirmed"
    COMMUNISM_CREATED = "communism_created"
    COMMUNISM_UPDATED = "communism_updated"
    COMMUNISM_CLOSED = "communism_closed"
    POLL_CREATED = "poll_created"
    POLL_UPDATED = "poll_updated"
    POLL_CLOSED = "poll_closed"
    REFUND_CREATED = "refund_created"
    REFUND_UPDATED = "refund_updated"
    REFUND_CLOSED = "refund_closed"
    TRANSACTION_CREATED = "transaction_created"
    VOUCHER_UPDATED = "voucher_updated"
    USER_SOFTLY_DELETED = "user_softly_deleted"


class Event(pydantic.BaseModel):
    event: EventType
    timestamp: pydantic.NonNegativeInt
    data: dict
