"""
MateBot extra schemas
"""

from typing import List

import pydantic

from .bases import User, UserAlias, Application, Transaction


class Refund(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    approval: List[pydantic.NonNegativeInt]
    refusal: List[pydantic.NonNegativeInt]


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
    applications: List[Application]
    alias: List[UserAlias]
    users: List[User]
    communisms: List[Communism]
    transactions: List[Transaction]
