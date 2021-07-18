"""
MateBot API schemas
"""

import uuid
from typing import List, Optional, Union

import pydantic


class IncomingUserAlias(pydantic.BaseModel):
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)


class UserAlias(pydantic.BaseModel):
    alias_id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)


class Application(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)


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


class Communism(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool
    externals: pydantic.NonNegativeInt
    participants: List[pydantic.NonNegativeInt]


class IncomingUser(pydantic.BaseModel):
    friendly_name: Optional[pydantic.constr(max_length=255)]
    balance: int = 0
    permission: bool
    active: bool
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]
    aliases: List[UserAlias]


class User(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    friendly_name: Optional[pydantic.constr(max_length=255)]
    balance: int
    permission: bool
    active: bool
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]
    aliases: List[UserAlias]
    created: pydantic.NonNegativeInt
    accessed: pydantic.NonNegativeInt
    communisms: List[Communism]


class IncomingTransaction(pydantic.BaseModel):
    sender: Union[pydantic.NonNegativeInt, UserAlias]
    receiver: Union[pydantic.NonNegativeInt, UserAlias]
    amount: pydantic.NonNegativeInt
    reason: pydantic.constr(max_length=255)


class Transaction(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    sender: pydantic.NonNegativeInt
    receiver: pydantic.NonNegativeInt
    amount: pydantic.NonNegativeInt
    reason: pydantic.constr(max_length=255)
    communism: Optional[pydantic.NonNegativeInt]
    refund: Optional[pydantic.NonNegativeInt]
    timestamp: pydantic.NonNegativeInt


class IncomingRefund(pydantic.BaseModel):
    amount: pydantic.PositiveInt
    description: pydantic.constr(max_length=255)
    creator: pydantic.NonNegativeInt
    active: bool = True


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
