"""
MateBot core database models
"""

import datetime

from sqlalchemy import (
    Boolean, DateTime, Integer, String,
    Column, FetchedValue, ForeignKey, UniqueConstraint
)
from sqlalchemy.orm import relationship, backref
from sqlalchemy.sql import func

from .database import Base


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

    id: int = _make_id_column()

    balance: int = Column(
        Integer,
        nullable=False,
        default=0
    )
    permission: bool = Column(
        Boolean,
        nullable=False,
        default=False
    )
    active: bool = Column(
        Boolean,
        nullable=False,
        default=True
    )
    external: bool = Column(
        Boolean,
        nullable=False
    )
    voucher_id: int = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=True
    )
    created: datetime.datetime = Column(
        DateTime,
        server_default=func.now()
    )
    accessed: datetime.datetime = Column(
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


class Application(Base):
    __tablename__ = "applications"

    id: int = _make_id_column()

    name: str = Column(
        String(255),
        nullable=False
    )

    aliases = relationship(
        "UserAlias",
        cascade="all,delete",
        backref="app"
    )


class UserAlias(Base):
    __tablename__ = "aliases"

    id: int = _make_id_column()

    user_id: int = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    app_id: int = Column(
        Integer,
        ForeignKey("applications.id", ondelete="CASCADE"),
        nullable=False
    )
    username: str = Column(
        String(255)
    )
    first_name: str = Column(
        String(255)
    )
    last_name: str = Column(
        String(255)
    )
    app_user_id: str = Column(
        String(255),
        nullable=False
    )

    __table_args__ = (
        UniqueConstraint("app_id", "app_user_id"),
    )


class Transaction(Base):
    __tablename__ = "transactions"

    id: int = _make_id_column()

    # TODO: reference to user ID
    sender: int = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )
    # TODO: reference to user ID
    receiver: int = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )
    amount: int = Column(
        Integer,
        nullable=False
    )
    reason: str = Column(
        String(255),
        nullable=True
    )
    registered: datetime.datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )


class Collective(Base):
    __tablename__ = "collectives"

    id: int = _make_id_column()

    active: bool = Column(
        Boolean,
        nullable=False,
        default=True
    )
    amount: int = Column(
        Integer,
        nullable=False
    )
    externals: int = Column(
        Integer,
        nullable=False,
        default=0
    )
    description: str = Column(
        String(255),
        nullable=True
    )
    communistic: bool = Column(
        Boolean,
        nullable=False
    )
    creator: int = Column(
        Integer,
        ForeignKey("users.id"),
        nullable=False
    )
    created: datetime.datetime = Column(
        DateTime,
        nullable=False,
        server_default=func.now()
    )
    accessed: datetime.datetime = Column(
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


class CollectivesUsers(Base):
    __tablename__ = "collectives_users"

    id: int = _make_id_column()

    collectives_id: int = Column(
        Integer,
        ForeignKey("collectives.id", ondelete="CASCADE"),
        nullable=False
    )
    users_id: int = Column(
        Integer,
        ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False
    )
    vote: bool = Column(
        Boolean,
        nullable=False
    )
