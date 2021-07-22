"""
MateBot core database models
"""

from sqlalchemy import (
    Boolean, DateTime, Integer, String,
    Column, FetchedValue, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from .database import Base
from .. import schemas


def _make_id_column():
    return Column(
        Integer,
        nullable=False,
        primary_key=True,
        autoincrement=True,
        unique=True
    )


class User(Base):
    __tablename__ = "users"

    id = _make_id_column()

    name = Column(
        String(255),
        nullable=True
    )
    balance = Column(
        Integer,
        nullable=False,
        default=0
    )
    permission = Column(
        Boolean,
        nullable=False,
        default=False
    )
    active = Column(
        Boolean,
        nullable=False,
        default=True
    )
    special = Column(
        Boolean,
        nullable=True,
        default=None,
        unique=True
    )
    external = Column(
        Boolean,
        nullable=False
    )
    voucher_id = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )
    created = Column(
        DateTime,
        server_default=func.now()
    )
    accessed = Column(
        DateTime,
        server_onupdate=FetchedValue(),
        server_default=func.now(),
        onupdate=func.now()
    )

    aliases = relationship(
        "UserAlias",
        cascade="all,delete",
        backref="user"
    )
    created_collectives = relationship(
        "Collective",
        backref="creator_user"
    )
    participating_collectives = relationship(
        "CollectivesUsers",
        backref="users"
    )
    vouching_for = relationship(
        "User",
        backref=backref("voucher_user", remote_side=[id])
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
            voucher=self.voucher_id,
            aliases=[alias.schema for alias in self.aliases],
            created=self.created.timestamp(),
            accessed=self.accessed.timestamp()
        )

    def __repr__(self) -> str:
        return f"User(id={self.id}, balance={self.balance}, aliases={self.aliases})"


class Application(Base):
    __tablename__ = "applications"

    id = _make_id_column()

    name = Column(
        String(255),
        nullable=False
    )

    aliases = relationship(
        "UserAlias",
        cascade="all,delete",
        backref="app"
    )

    @property
    def schema(self) -> schemas.Application:
        return schemas.Application(
            id=self.id,
            name=self.name
        )

    def __repr__(self) -> str:
        return f"Application(id={self.id}, name={self.name})"


class UserAlias(Base):
    __tablename__ = "aliases"

    id = _make_id_column()

    user_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    app_id = Column(
        Integer,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False
    )
    app_user_id = Column(
        String(255),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("app_id", "app_user_id"),
    )

    @property
    def schema(self) -> schemas.UserAlias:
        return schemas.UserAlias(
            alias_id=self.id,
            user_id=self.user_id,
            application=self.app.name,
            app_user_id=self.app_user_id
        )

    def __repr__(self) -> str:
        return "UserAlias(id={}, user_id={}, app_id={}, app_user_id={})".format(
            self.id, self.user_id, self.app_id, self.app_user_id
        )


class Transaction(Base):
    __tablename__ = "transactions"

    id = _make_id_column()

    # TODO: reference to user ID
    sender = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )
    # TODO: reference to user ID
    receiver = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )
    amount = Column(
        Integer,
        nullable=False
    )
    reason = Column(
        String(255),
        nullable=True
    )
    registered = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    collective_id = Column(
        Integer,
        ForeignKey("collectives.id"),
        nullable=True
    )

    collective = relationship(
        "Collective"
    )

    __table_args__ = (
        UniqueConstraint("sender", "receiver", "collective_id"),
    )

    def __repr__(self) -> str:
        return "Transaction(id={}, sender={}, receiver={}, amount={})".format(
            self.id, self.sender, self.receiver, self.amount
        )


class Collective(Base):
    __tablename__ = "collectives"

    id = _make_id_column()

    active = Column(
        Boolean,
        nullable=False,
        default=True
    )
    amount = Column(
        Integer,
        nullable=False
    )
    externals = Column(
        Integer,
        nullable=False,
        default=0
    )
    description = Column(
        String(255),
        nullable=True
    )
    communistic = Column(
        Boolean,
        nullable=False
    )
    creator = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )
    created = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    accessed = Column(
        DateTime,
        nullable=False,
        server_default=func.now(),
        onupdate=func.now()
    )

    participating_users = relationship(
        "CollectivesUsers",
        cascade="all,delete",
        backref="collective"
    )

    def __repr__(self) -> str:
        return f"Collective(id={self.id}, amount={self.amount}, creator={self.creator})"


class CollectivesUsers(Base):
    __tablename__ = "collectives_users"

    id = _make_id_column()

    collectives_id = Column(
        Integer,
        ForeignKey("collectives.id", ondelete="CASCADE"),
        nullable=False
    )
    users_id = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    vote = Column(
        Boolean,
        nullable=False
    )

    def __repr__(self) -> str:
        return f"CollectivesUsers(id={self.id})"
