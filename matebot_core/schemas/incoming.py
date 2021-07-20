"""
MateBot schemas for incoming (not yet existing) models
"""

import uuid
from typing import List, Optional, Union

import pydantic

from .bases import UserAlias


class IncomingUserAlias(pydantic.BaseModel):
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)


class IncomingApplication(pydantic.BaseModel):
    name: pydantic.constr(max_length=255)
    auth_token: uuid.UUID
    special_user: UserAlias


class IncomingCommunism(pydantic.BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool = True
    externals: pydantic.NonNegativeInt = 0
    participants: List[Union[pydantic.NonNegativeInt, UserAlias]] = []


class IncomingUser(pydantic.BaseModel):
    name: Optional[pydantic.constr(max_length=255)]
    balance: int = 0
    permission: bool
    active: bool
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]
    aliases: List[UserAlias]


class IncomingTransaction(pydantic.BaseModel):
    sender: Union[pydantic.NonNegativeInt, UserAlias]
    receiver: Union[pydantic.NonNegativeInt, UserAlias]
    amount: pydantic.NonNegativeInt
    reason: pydantic.constr(max_length=255)


class IncomingRefund(pydantic.BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool = True
