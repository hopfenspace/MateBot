"""
MateBot schemas for group actions

This module contains schemas for refunds
and its votes as well as communisms.
"""

import enum
from typing import List, Optional

import pydantic

from .bases import user_spec, MultiTransaction as _MultiTransaction, Transaction as _Transaction, User as _User


class Vote(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    user_name: pydantic.constr(max_length=255)
    ballot_id: pydantic.NonNegativeInt
    vote: bool
    modified: pydantic.NonNegativeInt


class VoteCreation(pydantic.BaseModel):
    user: user_spec
    ballot_id: pydantic.NonNegativeInt
    vote: bool


class Ballot(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt
    votes: List[Vote]


@enum.unique
class PollVariant(str, enum.Enum):
    GET_INTERNAL = "get_internal"
    LOOSE_INTERNAL = "loose_internal"
    GET_PERMISSION = "get_permission"
    LOOSE_PERMISSION = "loose_permission"


class Poll(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    active: bool
    accepted: Optional[bool]
    variant: PollVariant
    user: _User
    creator_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    votes: List[Vote]
    created: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt


class PollCreation(pydantic.BaseModel):
    user: user_spec
    issuer: user_spec
    variant: PollVariant


class PollVoteResponse(pydantic.BaseModel):
    poll: Poll
    vote: Vote


class Refund(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: _User
    active: bool
    allowed: Optional[bool]
    ballot_id: pydantic.NonNegativeInt
    votes: List[Vote]
    transaction: Optional[_Transaction]
    created: Optional[pydantic.NonNegativeInt]
    modified: Optional[pydantic.NonNegativeInt]


class RefundCreation(pydantic.BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: user_spec


class RefundVoteResponse(pydantic.BaseModel):
    refund: Refund
    vote: Vote


class CommunismUserBinding(pydantic.BaseModel):
    user_id: pydantic.NonNegativeInt
    user_name: pydantic.constr(max_length=255)
    quantity: pydantic.NonNegativeInt


class Communism(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator_id: pydantic.NonNegativeInt
    active: bool
    created: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt
    participants: List[CommunismUserBinding]
    multi_transaction: Optional[_MultiTransaction]


class CommunismCreation(pydantic.BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: user_spec


class CommunismParticipationUpdate(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user: user_spec


class CommunismUser(pydantic.BaseModel):
    communism: Communism
    user: _User
    quantity: pydantic.NonNegativeInt
