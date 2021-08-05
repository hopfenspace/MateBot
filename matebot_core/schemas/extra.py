"""
MateBot extra schemas

This module contains the special schemas for updates and the status.
"""

import uuid
import datetime

import pydantic


class Updates(pydantic.BaseModel):
    aliases: uuid.UUID
    applications: uuid.UUID
    ballots: uuid.UUID
    communisms: uuid.UUID
    consumables: uuid.UUID
    refunds: uuid.UUID
    transactions: uuid.UUID
    users: uuid.UUID
    votes: uuid.UUID
    timestamp: pydantic.NonNegativeInt


class Status(pydantic.BaseModel):
    healthy: bool
    startup: pydantic.NonNegativeInt
    datetime: datetime.datetime
    timestamp: pydantic.NonNegativeInt
