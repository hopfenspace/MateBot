"""
MateBot core database models
"""

import pydantic
from sqlalchemy import (
    Boolean, DateTime, Integer, SmallInteger, String,
    CheckConstraint, Column, FetchedValue, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from .database import Base
from .. import schemas


class Password(Base):
    __tablename__ = "passwords"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    salt = Column(String(255), nullable=False)
    passwd = Column(String(255), nullable=False)

    def __repr__(self) -> str:
        return f"Password(id={self.id})"


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    name = Column(String(255), nullable=True)
    balance = Column(Integer, nullable=False, default=0)
    permission = Column(Boolean, nullable=False, default=False)
    active = Column(Boolean, nullable=False, default=True)
    special = Column(Boolean, nullable=True, default=None, unique=True)
    external = Column(Boolean, nullable=False)
    voucher_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    created = Column(DateTime, server_default=func.now())
    accessed = Column(DateTime, server_onupdate=FetchedValue(), server_default=func.now(), onupdate=func.now())

    aliases = relationship("Alias", cascade="all,delete", backref="user")
    vouching_for = relationship("User", backref=backref("voucher_user", remote_side=[id]))

    __table_args__ = (
        CheckConstraint("special != false"),
    )

    @property
    def schema(self) -> schemas.User:
        return schemas.User(
            id=self.id,
            name=self.name,
            balance=self.balance,
            permission=self.permission,
            active=self.active,
            external=self.external,
            voucher_id=self.voucher_id,
            aliases=[alias.schema for alias in self.aliases],
            created=self.created.timestamp(),
            accessed=self.accessed.timestamp()
        )

    def __repr__(self) -> str:
        return f"User(id={self.id}, balance={self.balance}, aliases={self.aliases})"


class Application(Base):
    __tablename__ = "applications"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    name = Column(String(255), unique=True, nullable=False)
    created = Column(DateTime, server_default=func.now())
    password_id = Column(Integer, ForeignKey("passwords.id"), unique=True, nullable=False)

    callbacks = relationship("Callback", back_populates="app", cascade="all,delete")
    password = relationship("Password", cascade="all,delete")

    @property
    def schema(self) -> schemas.Application:
        return schemas.Application(
            id=self.id,
            name=self.name,
            created=self.created.timestamp()
        )

    def __repr__(self) -> str:
        return f"Application(id={self.id}, name={self.name})"


class Alias(Base):
    __tablename__ = "aliases"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    app_username = Column(String(255), nullable=False)
    confirmed = Column(Boolean, nullable=False, default=False)
    unique = Column(Boolean, nullable=False, default=True)

    application = relationship("Application", foreign_keys=[application_id])

    __table_args__ = (
        UniqueConstraint("application_id", "app_username"),
        UniqueConstraint("application_id", "user_id")
    )

    @property
    def schema(self) -> schemas.Alias:
        return schemas.Alias(
            id=self.id,
            user_id=self.user_id,
            application_id=self.application_id,
            app_username=self.app_username,
            confirmed=self.confirmed,
            unique=self.unique
        )

    def __repr__(self) -> str:
        return "Alias(id={}, user_id={}, application_id={}, app_username={})".format(
            self.id, self.user_id, self.application_id, self.app_username
        )


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    sender_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    reason = Column(String(255), nullable=True)
    registered = Column(DateTime, nullable=False, server_default=func.now())
    multi_transaction_id = Column(Integer, ForeignKey("multi_transaction.id"), nullable=True, default=None)

    sender = relationship("User", foreign_keys=[sender_id])
    receiver = relationship("User", foreign_keys=[receiver_id])
    multi_transaction = relationship("MultiTransaction", backref="transactions")

    __table_args__ = (
        CheckConstraint("amount > 0"),
        CheckConstraint("sender_id != receiver_id")
    )

    @property
    def schema(self) -> schemas.Transaction:
        return schemas.Transaction(
            id=self.id,
            sender=self.sender.schema,
            receiver=self.receiver.schema,
            amount=self.amount,
            reason=self.reason,
            multi_transaction_id=self.multi_transaction_id,
            timestamp=self.registered.timestamp()
        )

    def __repr__(self) -> str:
        return "Transaction(id={}, sender_id={}, receiver_id={}, amount={})".format(
            self.id, self.sender_id, self.receiver_id, self.amount
        )


class MultiTransaction(Base):
    __tablename__ = "multi_transaction"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    base_amount = Column(Integer, nullable=False)
    registered = Column(DateTime, nullable=False, server_default=func.now())

    @property
    def schema(self) -> schemas.MultiTransaction:
        return schemas.MultiTransaction(
            id=self.id,
            base_amount=self.base_amount,
            total_amount=sum(t.amount for t in self.transactions),
            transactions=list(map(lambda x: x.schema, self.transactions)),
            timestamp=self.registered.timestamp()
        )

    def __repr__(self) -> str:
        return "MultiTransaction(id={}, base_amount={})".format(
            self.id, self.base_amount
        )


class Consumable(Base):
    __tablename__ = "consumables"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    name = Column(String(255), unique=True)
    description = Column(String(255), nullable=False, default="")
    price = Column(Integer, nullable=False)
    symbol = Column(String(15), nullable=False)
    stock = Column(Integer, nullable=False)
    modified = Column(DateTime, server_onupdate=FetchedValue(), server_default=func.now(), onupdate=func.now())

    messages = relationship("ConsumableMessage", back_populates="consumable", cascade="all,delete")

    __table_args__ = (
        CheckConstraint("price > 0"),
        CheckConstraint("stock >= 0")
    )

    @property
    def schema(self) -> schemas.Consumable:
        return schemas.Consumable(
            id=self.id,
            name=self.name,
            description=self.description,
            price=self.price,
            messages=[msg.schema for msg in self.messages],
            symbol=self.symbol,
            stock=self.stock,
            modified=self.modified.timestamp()
        )

    def __repr__(self) -> str:
        return f"Consumable(id={self.id}, name={self.name}, price={self.price})"


class ConsumableMessage(Base):
    __tablename__ = "consumables_messages"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    consumable_id = Column(Integer, ForeignKey("consumables.id", ondelete="CASCADE"), nullable=False)
    message = Column(String(255), nullable=False)

    consumable = relationship("Consumable", back_populates="messages")

    @property
    def schema(self) -> pydantic.constr(max_length=255):
        return self.message

    def __repr__(self) -> str:
        return f"ConsumableMessage(id={self.id}, message={self.message!r})"


class Refund(Base):
    __tablename__ = "refunds"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    amount = Column(Integer, nullable=False)
    description = Column(String(255), nullable=True)
    active = Column(Boolean, nullable=False, default=True)
    created = Column(DateTime, nullable=False, server_default=func.now())
    accessed = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=True)
    poll_id = Column(Integer, ForeignKey("polls.id"), nullable=False)

    creator = relationship("User", backref="refunds")
    transaction = relationship("Transaction")
    poll = relationship("Poll")

    __table_args__ = (
        CheckConstraint("amount > 0"),
    )

    @property
    def schema(self) -> schemas.Refund:
        return schemas.Refund(
            id=self.id,
            amount=self.amount,
            description=self.description,
            creator=self.creator.schema,
            active=self.active,
            allowed=None if self.active else self.transaction is not None,
            poll_id=self.poll_id,
            transactions=self.transaction,
            created=self.created.timestamp(),
            accessed=self.accessed.timestamp()
        )

    def __repr__(self) -> str:
        return "Refund(id={}, creator={}, amount={}, description={})".format(
            self.id, self.creator, self.amount, self.description
        )


class Poll(Base):
    __tablename__ = "polls"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    question = Column(String(255), nullable=False)
    changeable = Column(Boolean, nullable=False)
    active = Column(Boolean, nullable=False, default=True)
    result = Column(Integer, nullable=True, default=None)
    closed = Column(DateTime, nullable=True, default=None)

    @property
    def schema(self) -> schemas.Poll:
        return schemas.Poll(
            id=self.id,
            question=self.question,
            changeable=self.changeable,
            active=self.active,
            votes=[vote.schema for vote in self.votes],
            result=self.result,
            closed=self.closed and self.closed.timestamp()
        )

    def __repr__(self) -> str:
        return "Poll(id={}, votes={})".format(
            self.id, [v.vote for v in self.votes]
        )


class Vote(Base):
    __tablename__ = "votes"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    poll_id = Column(Integer, ForeignKey("polls.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    vote = Column(SmallInteger, nullable=False)
    modified = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    poll = relationship("Poll", backref="votes")
    user = relationship("User", backref="votes")

    __table_args__ = (
        CheckConstraint("vote <= 1"),
        CheckConstraint("vote >= -1"),
        UniqueConstraint("user_id", "poll_id"),
    )

    @property
    def schema(self) -> schemas.Vote:
        return schemas.Vote(
            id=self.id,
            user_id=self.user_id,
            poll_id=self.poll_id,
            vote=self.vote,
            modified=self.modified.timestamp()
        )

    def __repr__(self) -> str:
        return "Vote(id={}, poll_id={}, user_id={}, vote={})".format(
            self.id, self.poll_id, self.user_id, self.vote
        )


class Communism(Base):
    __tablename__ = "communisms"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    active = Column(Boolean, nullable=False, default=True)
    amount = Column(Integer, nullable=False)
    description = Column(String(255), nullable=False)
    created = Column(DateTime, nullable=False, server_default=func.now())
    accessed = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    creator_id = Column(Integer, ForeignKey("users.id"), nullable=False)

    creator = relationship("User")
    participants = relationship("CommunismUsers", cascade="all,delete", backref="communism")

    __table_args__ = (
        CheckConstraint("amount >= 1"),
    )

    @property
    def schema(self) -> schemas.Communism:
        return schemas.Communism(
            id=self.id,
            amount=self.amount,
            description=self.description,
            creator=self.creator.schema,
            active=self.active,
            created=self.created.timestamp(),
            accessed=self.accessed.timestamp(),
            participants=[
                schemas.CommunismUserBinding(user_id=p.user_id, quantity=p.quantity)
                for p in self.participants
            ]
        )

    def __repr__(self) -> str:
        return f"Communism(id={self.id}, amount={self.amount}, creator={self.creator})"


class CommunismUsers(Base):
    __tablename__ = "communisms_users"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    communism_id = Column(Integer, ForeignKey("communisms.id", ondelete="CASCADE"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quantity = Column(Integer, nullable=False)

    user = relationship("User", backref="communisms")

    __table_args = (
        CheckConstraint("quantity >= 0"),
        UniqueConstraint("user_id", "communism_id"),
    )

    @property
    def schema(self) -> schemas.CommunismUser:
        return schemas.CommunismUser(
            communism=self.communism.schema,
            user=self.user.schema,
            quantity=self.quantity
        )

    def __repr__(self) -> str:
        return f"CommunismUsers(id={self.id}, user={self.user}, quantity={self.quantity})"


class Callback(Base):
    __tablename__ = "callbacks"

    id = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    base = Column(String(255), unique=False, nullable=False)
    application_id = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, unique=True)
    username = Column(String(255), nullable=True)
    password = Column(String(255), nullable=True)
    app = relationship("Application", back_populates="callbacks")

    @property
    def schema(self) -> schemas.Callback:
        return schemas.Callback(
            id=self.id,
            base=self.base,
            application_id=self.application_id,
            username=self.username,
            password=self.password
        )

    def __repr__(self) -> str:
        return f"Callback(id={self.id}, base={self.base}, application_id={self.application_id})"


# Asserting that every database model has a `schema` attribute
assert not any(
    True
    for mapper in Base.registry.mappers
    if not hasattr(mapper.class_, "schema")
    and mapper.class_.__name__ not in ["Password"]
)
