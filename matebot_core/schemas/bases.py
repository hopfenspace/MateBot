"""
MateBot schemas for the base system

This module contains schemas for users, their aliases,
applications and the transactions between the users as
well as the schemas needed for managing and consuming goods.
"""

from typing import List, Optional, Union

import pydantic


user_spec = Union[pydantic.NonNegativeInt, pydantic.constr(max_length=255)]


class IdBody(pydantic.BaseModel):
    id: pydantic.NonNegativeInt


class IssuerIdBody(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    issuer: user_spec


class Token(pydantic.BaseModel):
    access_token: str
    token_type: str


class Alias(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    user_id: pydantic.NonNegativeInt
    application_id: pydantic.NonNegativeInt
    username: pydantic.constr(max_length=255)
    confirmed: bool


class AliasCreation(pydantic.BaseModel):
    user_id: pydantic.NonNegativeInt
    application_id: pydantic.NonNegativeInt
    username: pydantic.constr(max_length=255)
    confirmed: bool = False


class AliasDeletion(pydantic.BaseModel):
    user_id: pydantic.NonNegativeInt
    aliases: List[Alias]


class Application(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    name: pydantic.constr(max_length=255)
    created: pydantic.NonNegativeInt


class User(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    balance: int
    name: pydantic.constr(max_length=255)
    permission: bool
    active: bool
    external: bool
    voucher_id: Optional[pydantic.NonNegativeInt]
    aliases: List[Alias]
    created: pydantic.NonNegativeInt
    modified: pydantic.NonNegativeInt


class UserCreation(pydantic.BaseModel):
    name: pydantic.constr(max_length=255)


class UserPrivilegeDrop(pydantic.BaseModel):
    user: user_spec
    issuer: Optional[user_spec]


class UsernameUpdateRequest(pydantic.BaseModel):
    name: pydantic.constr(max_length=255)
    issuer: user_spec


class Transaction(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    sender: User
    receiver: User
    amount: pydantic.NonNegativeInt
    reason: Optional[pydantic.constr(max_length=255)]
    multi_transaction_id: Optional[pydantic.NonNegativeInt]
    timestamp: pydantic.NonNegativeInt


class TransactionCreation(pydantic.BaseModel):
    sender: user_spec
    receiver: user_spec
    amount: pydantic.PositiveInt
    reason: pydantic.constr(max_length=255)


class MultiTransaction(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    base_amount: pydantic.NonNegativeInt
    total_amount: pydantic.NonNegativeInt
    transactions: List[Transaction]
    timestamp: pydantic.NonNegativeInt


class Consumable(pydantic.BaseModel):
    name: pydantic.constr(max_length=255)
    description: pydantic.constr(max_length=255)
    price: pydantic.PositiveInt
    emoji: pydantic.constr(max_length=2)


class Consumption(pydantic.BaseModel):
    user: user_spec
    amount: pydantic.PositiveInt
    consumable: pydantic.constr(max_length=255)


class VoucherUpdateResponse(pydantic.BaseModel):
    debtor: User
    voucher: Optional[User]
    transaction: Optional[Transaction]


class VoucherUpdateRequest(pydantic.BaseModel):
    debtor: user_spec
    voucher: Optional[user_spec]
    issuer: user_spec
