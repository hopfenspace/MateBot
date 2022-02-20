"""
MateBot schemas for group actions

This module contains schemas for refunds
and its votes as well as communisms.
"""

from typing import List, Optional

import pydantic

from .bases import MultiTransaction as _MultiTransaction, Transaction as _Transaction, User as _User, BaseModel


class Vote(BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    vote: bool
    modified: pydantic.NonNegativeInt


class VoteCreation(BaseModel):
    user_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    vote: bool


class Ballot(BaseModel):
    id: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt
    votes: List[Vote]


class Poll(BaseModel):
    id: pydantic.NonNegativeInt
    active: bool
    accepted: Optional[bool]
    creator: _User
    votes: List[Vote]
    created: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt


class PollCreation(BaseModel):
    creator_id: pydantic.NonNegativeInt


class Refund(BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: _User
    active: bool
    allowed: Optional[bool]
    votes: List[Vote]
    transaction: Optional[_Transaction]
    created: Optional[pydantic.NonNegativeInt]
    modified: Optional[pydantic.NonNegativeInt]


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
    modified: pydantic.NonNegativeInt
    participants: List[CommunismUserBinding]
    multi_transaction: Optional[_MultiTransaction]


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
