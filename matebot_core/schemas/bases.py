"""
MateBot schemas for the base system

This module contains schemas for users, their aliases,
applications and the transactions between the users as
well as the schemas needed for managing and consuming goods.
"""

from typing import List, Optional, Union

import pydantic


UUID_REGEX = r"^\b[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b$"


class BaseModel(pydantic.BaseModel):
    __allowed_updates__ = []


class Token(BaseModel):
    access_token: str
    token_type: str


class Alias(BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)
    confirmed: bool

    __allowed_updates__ = ["app_user_id", "confirmed"]


class AliasCreation(BaseModel):
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)
    confirmed: bool = False


class Application(BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    community_user: Alias
    created: pydantic.NonNegativeInt


class ApplicationCreation(BaseModel):
    name: pydantic.constr(max_length=255)
    password: pydantic.constr(min_length=8, max_length=64)
    community_user_name: pydantic.constr(max_length=255)


class User(BaseModel):
    id: pydantic.NonNegativeInt
    name: Optional[pydantic.constr(max_length=255)]
    balance: int
    permission: bool
    active: bool
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]
    aliases: List[Alias]
    created: pydantic.NonNegativeInt
    accessed: pydantic.NonNegativeInt

    __allowed_updates__ = ["name", "permission", "active", "external", "voucher"]


class UserCreation(BaseModel):
    name: Optional[pydantic.constr(max_length=255)]
    permission: bool
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]


class Transaction(BaseModel):
    id: pydantic.NonNegativeInt
    sender: pydantic.NonNegativeInt
    receiver: pydantic.NonNegativeInt
    amount: pydantic.NonNegativeInt
    reason: Optional[pydantic.constr(max_length=255)]
    multi_transaction: Optional[pydantic.NonNegativeInt]
    timestamp: pydantic.NonNegativeInt


class TransactionCreation(BaseModel):
    sender: Union[pydantic.NonNegativeInt, Alias]
    receiver: Union[pydantic.NonNegativeInt, Alias]
    amount: pydantic.PositiveInt
    reason: pydantic.constr(max_length=255)


class MultiTransaction(BaseModel):
    id: pydantic.NonNegativeInt
    base_amount: pydantic.NonNegativeInt
    total_amount: pydantic.NonNegativeInt
    transactions: List[Transaction]
    timestamp: pydantic.NonNegativeInt


class Consumable(BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    description: pydantic.constr(max_length=255)
    price: pydantic.PositiveInt
    messages: List[pydantic.constr(max_length=255)]
    symbol: pydantic.constr(min_length=1, max_length=1)
    stock: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt

    __allowed_updates__ = ["name", "description", "price", "messages", "symbol", "stock"]


class ConsumableCreation(BaseModel):
    name: pydantic.constr(max_length=255)
    description: pydantic.constr(max_length=255) = ""
    price: pydantic.PositiveInt
    messages: List[pydantic.constr(max_length=255)]
    symbol: pydantic.constr(min_length=1, max_length=1)
    stock: pydantic.NonNegativeInt


class Consumption(BaseModel):
    user: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    consumable_id: pydantic.NonNegativeInt
    adjust_stock: bool = True
    respect_stock: bool = True
