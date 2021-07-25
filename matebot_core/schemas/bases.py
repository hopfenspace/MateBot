"""
MateBot base schemas
"""

from typing import List, Optional

import pydantic


UUID_REGEX = r"^\b[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b$"


class Vote(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    ballot_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)
    modified: pydantic.NonNegativeInt


class Ballot(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    question: pydantic.constr(max_length=255)
    restricted: bool
    active: bool
    votes: List[Vote]
    result: Optional[int]
    closed: Optional[pydantic.NonNegativeInt]


class UserAlias(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    alias_id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)


class Application(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)


class User(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: Optional[pydantic.constr(max_length=255)]
    balance: int
    permission: bool
    active: bool
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]
    aliases: List[UserAlias]
    created: pydantic.NonNegativeInt
    accessed: pydantic.NonNegativeInt


class TransactionType(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    count: pydantic.NonNegativeInt


class Transaction(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    sender: pydantic.NonNegativeInt
    receiver: pydantic.NonNegativeInt
    amount: pydantic.NonNegativeInt
    reason: pydantic.constr(max_length=255)
    transaction_type: TransactionType
    timestamp: pydantic.NonNegativeInt
