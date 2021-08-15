"""
MateBot schemas for the base system

This module contains schemas for users, their aliases,
applications and the transactions between the users as
well as the schemas needed for managing and consuming goods.
"""

from typing import List, Optional, Union

import pydantic


UUID_REGEX = r"^\b[0-9a-fA-F]{8}-([0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b$"


class Alias(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)


class AliasCreation(pydantic.BaseModel):
    user_id: pydantic.NonNegativeInt
    application: pydantic.constr(max_length=255)
    app_user_id: pydantic.constr(max_length=255)


class Application(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    community_user: Alias
    created: pydantic.NonNegativeInt


class ApplicationCreation(pydantic.BaseModel):
    name: pydantic.constr(max_length=255)
    community_user: AliasCreation


class User(pydantic.BaseModel):
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


class UserCreation(pydantic.BaseModel):
    name: Optional[pydantic.constr(max_length=255)]
    permission: bool
    active: bool = True
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]


class UserUpdate(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: Optional[pydantic.constr(max_length=255)]
    permission: bool
    active: bool
    external: bool
    voucher: Optional[pydantic.NonNegativeInt]


class TransactionType(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    count: pydantic.NonNegativeInt


class Transaction(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    sender: pydantic.NonNegativeInt
    receiver: pydantic.NonNegativeInt
    amount: pydantic.NonNegativeInt
    reason: Optional[pydantic.constr(max_length=255)]
    transaction_type: TransactionType
    timestamp: pydantic.NonNegativeInt


class TransactionCreation(pydantic.BaseModel):
    sender: Union[pydantic.NonNegativeInt, Alias]
    receiver: Union[pydantic.NonNegativeInt, Alias]
    amount: pydantic.PositiveInt
    reason: pydantic.constr(max_length=255)


class Consumable(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    description: pydantic.constr(max_length=255)
    price: pydantic.PositiveInt
    messages: List[pydantic.constr(max_length=255)]
    symbol: pydantic.constr(min_length=1, max_length=1)
    stock: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt


class ConsumableCreation(pydantic.BaseModel):
    name: pydantic.constr(max_length=255)
    description: pydantic.constr(max_length=255) = ""
    price: pydantic.PositiveInt
    messages: List[pydantic.constr(max_length=255)]
    symbol: pydantic.constr(min_length=1, max_length=1)
    stock: pydantic.NonNegativeInt


class ConsumableUpdate(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    description: pydantic.constr(max_length=255) = ""
    price: pydantic.PositiveInt
    messages: List[pydantic.constr(max_length=255)]
    symbol: pydantic.constr(min_length=1, max_length=2)
    stock: pydantic.NonNegativeInt


class Consumption(pydantic.BaseModel):
    user: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    consumable_id: pydantic.NonNegativeInt
    adjust_stock: bool = True
    respect_stock: bool = True
