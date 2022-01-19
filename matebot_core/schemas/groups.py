"""
MateBot schemas for group actions

This module contains schemas for polls and its
votes as well as communisms and refunds.
"""

from typing import List, Optional

import pydantic

from .bases import MultiTransaction as _MultiTransaction, Transaction as _Transaction, User as _User, BaseModel


class Vote(BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    poll_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)
    modified: pydantic.NonNegativeInt

    __allowed_updates__ = ["vote"]


class VoteCreation(BaseModel):
    user_id: pydantic.NonNegativeInt
    poll_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)


class Poll(BaseModel):
    id: pydantic.NonNegativeInt
    question: pydantic.constr(max_length=255)
    changeable: bool
    active: bool
    votes: List[Vote]
    result: Optional[int]
    closed: Optional[pydantic.NonNegativeInt]

    __allowed_updates__ = ["active"]


class PollCreation(BaseModel):
    question: pydantic.constr(max_length=255)
    changeable: bool


class Refund(BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: _User
    active: bool
    allowed: Optional[bool]
    poll: Poll
    transaction: Optional[_Transaction]
    created: Optional[pydantic.NonNegativeInt]
    accessed: Optional[pydantic.NonNegativeInt]

    __allowed_updates__ = ["active"]


class RefundCreation(BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator_id: pydantic.NonNegativeInt
    active: bool = True


class CommunismUserBinding(BaseModel):
    user_id: pydantic.NonNegativeInt
    quantity: pydantic.NonNegativeInt


class Communism(BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator_id: pydantic.NonNegativeInt
    active: bool
    created: pydantic.NonNegativeInt
    accessed: pydantic.NonNegativeInt
    participants: List[CommunismUserBinding]
    multi_transaction: Optional[_MultiTransaction]

    __allowed_updates__ = ["active", "participants"]


class CommunismCreation(BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator_id: pydantic.NonNegativeInt
    active: bool = True
    participants: List[CommunismUserBinding] = []


class CommunismUser(BaseModel):
    communism: Communism
    user: _User
    quantity: pydantic.NonNegativeInt
