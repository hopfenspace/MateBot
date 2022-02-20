"""
MateBot schemas for the base system

This module contains schemas for users, their aliases,
applications and the transactions between the users as
well as the schemas needed for managing and consuming goods.
"""

from typing import List, Optional

import pydantic


class BaseModel(pydantic.BaseModel):
    __allowed_updates__ = []


class Token(BaseModel):
    access_token: str
    token_type: str


class Alias(BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    application_id: pydantic.NonNegativeInt
    app_username: pydantic.constr(max_length=255)
    confirmed: bool
    unique: bool

    __allowed_updates__ = ["app_username", "confirmed"]


class AliasCreation(BaseModel):
    user_id: pydantic.NonNegativeInt
    application_id: pydantic.NonNegativeInt
    app_username: pydantic.constr(max_length=255)
    confirmed: bool = False
    unique: bool = True


class Application(BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    created: pydantic.NonNegativeInt


class ApplicationCreation(BaseModel):
    name: pydantic.constr(max_length=255)
    password: pydantic.constr(min_length=8, max_length=64)


class User(BaseModel):
    id: pydantic.NonNegativeInt
    name: Optional[pydantic.constr(max_length=255)]
    balance: int
    permission: bool
    active: bool
    external: bool
    voucher_id: Optional[pydantic.NonNegativeInt]
    aliases: List[Alias]
    created: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt

    __allowed_updates__ = ["name", "permission", "external"]


class UserCreation(BaseModel):
    name: Optional[pydantic.constr(max_length=255)]
    permission: bool
    external: bool
    voucher_id: Optional[pydantic.NonNegativeInt]


class Transaction(BaseModel):
    id: pydantic.NonNegativeInt
    sender: User
    receiver: User
    amount: pydantic.NonNegativeInt
    reason: Optional[pydantic.constr(max_length=255)]
    multi_transaction_id: Optional[pydantic.NonNegativeInt]
    timestamp: pydantic.NonNegativeInt


class TransactionCreation(BaseModel):
    sender_id: pydantic.NonNegativeInt
    receiver_id: pydantic.NonNegativeInt
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


class Consumption(BaseModel):
    user_id: pydantic.NonNegativeInt
    amount: pydantic.PositiveInt
    consumable_id: pydantic.NonNegativeInt
    adjust_stock: bool = True
    respect_stock: bool = True


class VoucherUpdateResponse(BaseModel):
    debtor: User
    voucher: Optional[User]
    transaction: Transaction


class VoucherUpdateRequest(BaseModel):
    debtor: pydantic.NonNegativeInt
    voucher: Optional[pydantic.NonNegativeInt]
