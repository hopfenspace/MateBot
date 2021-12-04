"""
MateBot schemas for group actions

This module contains schemas for ballots and its
votes as well as communisms and refunds.
"""

from typing import List, Optional

import pydantic

from .bases import Transaction as _Transaction, User as _User, BaseModel


class Vote(BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)
    modified: pydantic.NonNegativeInt

    __allowed_updates__ = ["vote"]


class VoteCreation(BaseModel):
    user_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)


class Ballot(BaseModel):
    id: pydantic.NonNegativeInt
    question: pydantic.constr(max_length=255)
    changeable: bool
    active: bool
    votes: List[Vote]
    result: Optional[int]
    closed: Optional[pydantic.NonNegativeInt]

    __allowed_updates__ = ["active"]


class BallotCreation(BaseModel):
    question: pydantic.constr(max_length=255)
    changeable: bool


class Refund(BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    allowed: Optional[bool]
    ballot: pydantic.NonNegativeInt
    transaction: Optional[_Transaction]
    created: Optional[pydantic.NonNegativeInt]
    accessed: Optional[pydantic.NonNegativeInt]

    __allowed_updates__ = ["active"]


class RefundCreation(BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool = True


class CommunismUserBinding(BaseModel):
    user: pydantic.NonNegativeInt
    quantity: pydantic.NonNegativeInt


class Communism(BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    accepted: Optional[bool]
    externals: pydantic.NonNegativeInt
    participants: List[CommunismUserBinding]
    transactions: Optional[List[_Transaction]]
    timestamp: Optional[pydantic.NonNegativeInt]

    __allowed_updates__ = ["active", "externals", "participants"]


class CommunismCreation(BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool = True
    externals: pydantic.NonNegativeInt = 0
    participants: List[CommunismUserBinding] = []


class CommunismUser(BaseModel):
    communism: Communism
    user: _User
    quantity: pydantic.NonNegativeInt
