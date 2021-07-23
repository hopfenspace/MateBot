"""
MateBot base schemas
"""

from typing import List, Optional

import pydantic


class Vote(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    vote: pydantic.conint(ge=-1, le=1)
    modified: pydantic.NonNegativeInt


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


class Transaction(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    sender: pydantic.NonNegativeInt
    receiver: pydantic.NonNegativeInt
    amount: pydantic.NonNegativeInt
    reason: pydantic.constr(max_length=255)
    communism: Optional[pydantic.NonNegativeInt]
    refund: Optional[pydantic.NonNegativeInt]
    timestamp: pydantic.NonNegativeInt
