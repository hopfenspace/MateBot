"""
MateBot extra schemas
"""

import uuid
import datetime
from typing import List, Optional

import pydantic

from .bases import Transaction


class Refund(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    allowed: Optional[bool]
    ballot: pydantic.NonNegativeInt


class SuccessfulRefund(pydantic.BaseModel):
    refund: Refund
    transactions: List[Transaction]
    timestamp: pydantic.NonNegativeInt


class Communism(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    externals: pydantic.NonNegativeInt
    participants: List[pydantic.NonNegativeInt]


class SuccessfulCommunism(pydantic.BaseModel):
    communism: Communism
    transactions: List[Transaction]
    timestamp: pydantic.NonNegativeInt


class Updates(pydantic.BaseModel):
    aliases: uuid.UUID
    applications: uuid.UUID
    ballots: uuid.UUID
    communisms: uuid.UUID
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
