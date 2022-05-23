"""
MateBot core database models
"""

import datetime
from typing import List

from sqlalchemy import (
    Boolean, DateTime, Integer, String,
    CheckConstraint, Column, FetchedValue, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from .database import Base
from .. import schemas


class User(Base):
    """
    Model representing one end-user of the MateBot via some client application
    """

    __tablename__ = "users"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    balance: int = Column(Integer, nullable=False, default=0)
    permission: bool = Column(Boolean, nullable=False, default=False)
    """Flag indicating whether the user is allowed to take part in ballots"""
    active: bool = Column(Boolean, nullable=False, default=True)
    """Flag indicating a disabled user (treated as 'deleted'), since user models won't be removed"""
    special: bool = Column(Boolean, nullable=True, default=None, unique=True)
    """Unique flag determining the special community user in the set of users"""
    external: bool = Column(Boolean, nullable=False)
    voucher_id: int = Column(Integer, ForeignKey("users.id"), nullable=True)
    created: datetime.datetime = Column(DateTime, server_default=func.now())
    modified: datetime.datetime = Column(DateTime, server_onupdate=FetchedValue(), server_default=func.now(), onupdate=func.now())

    aliases: List["Alias"] = relationship("Alias", cascade="all,delete", backref="user")
    vouching_for: List["User"] = relationship("User", backref=backref("voucher_user", remote_side=[id]))

    __table_args__ = (
        CheckConstraint("special != false"),
    )

    @property
    def schema(self) -> schemas.User:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.User(
            id=self.id,
            balance=self.balance,
            permission=self.permission,
            active=self.active,
            external=self.external,
            voucher_id=self.voucher_id,
            aliases=[alias.schema for alias in self.aliases],
            created=self.created.timestamp(),
            modified=self.modified.timestamp()
        )

    def __repr__(self) -> str:
        return f"User(id={self.id}, balance={self.balance}, aliases={self.aliases})"


class Application(Base):
    """
    Model representing a front-end (client) application to this backend service
    """

    __tablename__ = "applications"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    name: str = Column(String(255), unique=True, nullable=False)
    password: str = Column(String(255), nullable=False)
    salt: str = Column(String(255), nullable=False)
    created: datetime.datetime = Column(DateTime, server_default=func.now())

    callbacks: List["Callback"] = relationship("Callback", back_populates="app", cascade="all,delete")

    @property
    def schema(self) -> schemas.Application:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Application(
            id=self.id,
            name=self.name,
            created=self.created.timestamp()
        )

    def __repr__(self) -> str:
        return f"Application(id={self.id}, name={self.name})"


class Alias(Base):
    """
    Model representing a unique user reference in a given application
    """

    __tablename__ = "aliases"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    user_id: int = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    application_id: int = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=False)
    username: str = Column(String(255), nullable=False)
    """User's unique username in the client application (may also be a user ID)"""
    confirmed: bool = Column(Boolean, nullable=False, default=False)
    """Flag indicating whether the alias was confirmed by the user via another application"""

    application: Application = relationship("Application", foreign_keys=[application_id])

    __table_args__ = (
        UniqueConstraint("application_id", "username", name="single_username_per_app"),
    )

    @property
    def schema(self) -> schemas.Alias:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Alias(
            id=self.id,
            user_id=self.user_id,
            application_id=self.application_id,
            username=self.username,
            confirmed=self.confirmed
        )

    def __repr__(self) -> str:
        return "Alias(id={}, user_id={}, application_id={}, username={})".format(
            self.id, self.user_id, self.application_id, self.username
        )


class Transaction(Base):
    """
    Model representing a single transaction record between exactly two users
    """

    __tablename__ = "transactions"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    sender_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    receiver_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    amount: int = Column(Integer, nullable=False)
    reason: str = Column(String(255), nullable=True)
    """Reason for the transaction which may be used as its description"""
    timestamp: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now())
    multi_transaction_id: int = Column(Integer, ForeignKey("multi_transactions.id"), nullable=True, default=None)

    sender: User = relationship("User", foreign_keys=[sender_id])
    receiver: User = relationship("User", foreign_keys=[receiver_id])
    multi_transaction: "MultiTransaction" = relationship("MultiTransaction", backref="transactions")

    __table_args__ = (
        CheckConstraint("amount > 0"),
        CheckConstraint("sender_id != receiver_id")
    )

    @property
    def schema(self) -> schemas.Transaction:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Transaction(
            id=self.id,
            sender=self.sender.schema,
            receiver=self.receiver.schema,
            amount=self.amount,
            reason=self.reason,
            multi_transaction_id=self.multi_transaction_id,
            timestamp=self.timestamp.timestamp()
        )

    def __repr__(self) -> str:
        return "Transaction(id={}, sender_id={}, receiver_id={}, amount={})".format(
            self.id, self.sender_id, self.receiver_id, self.amount
        )


class MultiTransaction(Base):
    """
    Model representing a series of transactions that are tied together via a group operation (e.g. communism)
    """

    __tablename__ = "multi_transactions"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    base_amount: int = Column(Integer, nullable=False)
    registered: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now())

    @property
    def schema(self) -> schemas.MultiTransaction:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

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


class Refund(Base):
    """
    Model representing a refund request which allows individual users to receive money from the community
    """

    __tablename__ = "refunds"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    amount: int = Column(Integer, nullable=False)
    description: str = Column(String(255), nullable=False)
    active: bool = Column(Boolean, nullable=False, default=True)
    created: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now())
    modified: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    creator_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    ballot_id: int = Column(Integer, ForeignKey("ballots.id"), nullable=False)
    transaction_id: int = Column(Integer, ForeignKey("transactions.id"), nullable=True)

    creator: User = relationship("User", backref="refunds")
    ballot: "Ballot" = relationship("Ballot", backref="refunds")
    transaction: Transaction = relationship("Transaction")

    __table_args__ = (
        CheckConstraint("amount > 0"),
    )

    @property
    def schema(self) -> schemas.Refund:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Refund(
            id=self.id,
            amount=self.amount,
            description=self.description,
            creator=self.creator.schema,
            active=self.active,
            allowed=None if self.active else self.transaction is not None,
            ballot_id=self.ballot_id,
            votes=[vote.schema for vote in self.ballot.votes],
            transaction=self.transaction and self.transaction.schema,
            created=self.created.timestamp(),
            modified=self.modified.timestamp()
        )

    def __repr__(self) -> str:
        return "Refund(id={}, creator={}, amount={}, description={})".format(
            self.id, self.creator, self.amount, self.description
        )


class Poll(Base):
    """
    Model representing a membership request poll to allow external users to be promoted to internals
    """

    __tablename__ = "polls"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    active: bool = Column(Boolean, nullable=False, default=True)
    accepted: bool = Column(Boolean, nullable=True, default=None)
    """Flag indicating whether the membership poll was accepted by the community"""
    creator_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    ballot_id: int = Column(Integer, ForeignKey("ballots.id"), nullable=False)
    created: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now())
    modified: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    creator: User = relationship("User", backref="polls")
    ballot: "Ballot" = relationship("Ballot", backref="polls")

    @property
    def schema(self) -> schemas.Poll:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Poll(
            id=self.id,
            active=self.active,
            accepted=self.accepted,
            created=self.created.timestamp(),
            modified=self.modified.timestamp(),
            creator=self.creator.schema,
            ballot_id=self.ballot_id,
            votes=[v.schema for v in self.ballot.votes]
        )

    def __repr__(self) -> str:
        return "Poll(id={}, creator={})".format(self.id, self.creator)


class Ballot(Base):
    """
    Model representing a ballot with one vote per user (used by polls and refunds)
    """

    __tablename__ = "ballots"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    modified: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    @property
    def result(self) -> int:
        """
        Convenience property returning the sum of all votes (= result of the ballot)
        """

        return -len(self.votes) + 2 * sum(v.vote for v in self.votes)

    @property
    def schema(self) -> schemas.Ballot:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Ballot(
            id=self.id,
            modified=self.modified.timestamp(),
            votes=[v.schema for v in self.votes]
        )

    def __repr__(self) -> str:
        return "Ballot(id={})".format(self.id)


class Vote(Base):
    """
    Model representing a unique vote in a ballot (with at most one vote per user)
    """

    __tablename__ = "votes"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    vote: bool = Column(Boolean, nullable=False)
    ballot_id: int = Column(Integer, ForeignKey("ballots.id", ondelete="CASCADE"), nullable=False)
    user_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    modified: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())

    ballot: Ballot = relationship("Ballot", backref="votes")
    user: User = relationship("User", backref="votes")

    __table_args__ = (
        UniqueConstraint("user_id", "ballot_id", name="single_vote_per_user"),
    )

    @property
    def schema(self) -> schemas.Vote:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Vote(
            id=self.id,
            user_id=self.user_id,
            ballot_id=self.ballot_id,
            vote=self.vote,
            modified=self.modified.timestamp()
        )

    def __repr__(self) -> str:
        return "Vote(id={}, ballot_id={}, user_id={}, vote={})".format(
            self.id, self.ballot_id, self.user_id, self.vote
        )


class Communism(Base):
    """
    Model representing a collective payment, where multiple users pay fractions of a total amount
    """

    __tablename__ = "communisms"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    active: bool = Column(Boolean, nullable=False, default=True)
    amount: int = Column(Integer, nullable=False)
    description: str = Column(String(255), nullable=False)
    created: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now())
    modified: datetime.datetime = Column(DateTime, nullable=False, server_default=func.now(), onupdate=func.now())
    creator_id: int = Column(Integer, ForeignKey("users.id"), nullable=False)
    multi_transaction_id: int = Column(Integer, ForeignKey("multi_transactions.id"), nullable=True, default=None)

    creator: User = relationship("User")
    participants: List["CommunismUsers"] = relationship("CommunismUsers", cascade="all,delete", backref="communism")
    multi_transaction: MultiTransaction = relationship("MultiTransaction")

    __table_args__ = (
        CheckConstraint("amount >= 1"),
    )

    @property
    def schema(self) -> schemas.Communism:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Communism(
            id=self.id,
            amount=self.amount,
            description=self.description,
            creator_id=self.creator_id,
            active=self.active,
            created=self.created.timestamp(),
            modified=self.modified.timestamp(),
            participants=[
                schemas.CommunismUserBinding(user_id=p.user_id, quantity=p.quantity)
                for p in self.participants
            ],
            multi_transaction=self.multi_transaction and self.multi_transaction.schema
        )

    def __repr__(self) -> str:
        return f"Communism(id={self.id}, amount={self.amount}, creator={self.creator})"


class CommunismUsers(Base):
    """
    Model representing a user that participates in one communism
    """

    __tablename__ = "communisms_users"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    communism_id: int = Column(Integer, ForeignKey("communisms.id", ondelete="CASCADE"), nullable=False)
    user_id: int = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    quantity: int = Column(Integer, nullable=False)
    """Number of times a user joined the communism, since users may decide to pay more than others"""

    user: User = relationship("User", backref="communisms")

    __table_args = (
        CheckConstraint("quantity >= 0"),
        UniqueConstraint("user_id", "communism_id", name="single_user_per_communism"),
    )

    @property
    def schema(self) -> schemas.CommunismUser:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.CommunismUser(
            communism=self.communism.schema,
            user=self.user.schema,
            quantity=self.quantity
        )

    def __repr__(self) -> str:
        return f"CommunismUsers(id={self.id}, user={self.user}, quantity={self.quantity})"


class Callback(Base):
    """
    Model representing a callback path to notify a client application about certain updates
    """

    __tablename__ = "callbacks"

    id: int = Column(Integer, nullable=False, primary_key=True, autoincrement=True, unique=True)
    url: str = Column(String(255), unique=False, nullable=False)
    """Callback URL used to notify the client application"""
    application_id: int = Column(Integer, ForeignKey("applications.id", ondelete="CASCADE"), nullable=True, unique=True)
    shared_secret: str = Column(String(2047), nullable=True)
    """Shared secret directly used in the HTTP Authorization header using the 'Bearer' scheme"""

    app: Application = relationship("Application", back_populates="callbacks")

    @property
    def schema(self) -> schemas.Callback:
        """
        Pydantic schema representation of the database model that can be sent to clients
        """

        return schemas.Callback(
            id=self.id,
            url=self.url,
            application_id=self.application_id,
            shared_secret=self.shared_secret
        )

    def __repr__(self) -> str:
        return f"Callback(id={self.id}, base={self.base}, application_id={self.application_id})"


# Asserting that every database model has a `schema` attribute
assert not any(True for mapper in Base.registry.mappers if not hasattr(mapper.class_, "schema"))
