"""
MateBot schemas for group actions

This module contains schemas for ballots and its
votes as well as communisms and refunds.
"""

from typing import List, Optional, Union

import pydantic

from .bases import Alias as _Alias, Transaction as _Transaction


class Vote(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)
    modified: pydantic.NonNegativeInt


class VoteCreation(pydantic.BaseModel):
    user_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)


class VoteUpdate(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)


class Ballot(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    question: pydantic.constr(max_length=255)
    restricted: bool
    active: bool
    votes: List[Vote]
    result: Optional[int]
    closed: Optional[pydantic.NonNegativeInt]


class BallotCreation(pydantic.BaseModel):
    question: pydantic.constr(max_length=255)
    restricted: bool


class Refund(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    allowed: Optional[bool]
    ballot: pydantic.NonNegativeInt
    transactions: Optional[List[_Transaction]]
    timestamp: Optional[pydantic.NonNegativeInt]


class RefundCreation(pydantic.BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool = True


class RefundPatch(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    cancelled: bool = False


class Communism(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    accepted: Optional[bool]
    externals: pydantic.NonNegativeInt
    participants: List[pydantic.NonNegativeInt]
    transactions: Optional[List[_Transaction]]
    timestamp: Optional[pydantic.NonNegativeInt]


class CommunismCreation(pydantic.BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool = True
    externals: pydantic.NonNegativeInt = 0
    participants: List[Union[pydantic.NonNegativeInt, _Alias]] = []


class CommunismPatch(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    active: Optional[bool]
    accepted: Optional[bool]
    externals: Optional[pydantic.NonNegativeInt]
    participants: Optional[List[Union[pydantic.NonNegativeInt, _Alias]]]
