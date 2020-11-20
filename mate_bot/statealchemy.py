import datetime
from typing import List

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Sequence, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import or_

from mate_bot.parsing.util import Representable


_Base = declarative_base()


class User(_Base, Representable):
    __tablename__ = "users"

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
    matrix_id = Column(String(255), unique=True)
    name = Column(String(255))
    username = Column(String(255))
    balance = Column(Integer, default=0)
    permission = Column(Integer, default=0)
    active = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.datetime.now)
    accessed = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    @property
    def external(self):
        return False

    @property
    def creditor(self):
        return True

    @staticmethod
    def push():
        SESSION.commit()

    @staticmethod
    def new(matrix_id: str, **kwargs) -> "User":
        user = User(matrix_id=matrix_id, **kwargs)
        SESSION.add(user)
        SESSION.commit()
        return user

    @staticmethod
    def get(matrix_id: str) -> "User":
        query = SESSION.query(User).filter_by(matrix_id=matrix_id)
        count = query.count()
        if count == 1:
            return query.first()
        elif count == 0:
            raise ValueError(f"No user with the id '{matrix_id}'")
        else:
            raise RuntimeError(f"The database is broken: Found more than one user with id '{matrix_id}'")

    @staticmethod
    def get_or_create(matrix_id: str, **kwargs) -> "User":
        try:
            return User.get(matrix_id)
        except ValueError:
            return User.new(matrix_id, **kwargs)

    @staticmethod
    def community_user():
        return SESSION.query(User).filter_by(id=1).first()


class Transaction(_Base):
    __tablename__ = "transactions"

    id = Column(Integer, Sequence("transaction_id_seq"), primary_key=True)
    sender = Column(ForeignKey("users.id"), nullable=False)
    receiver = Column(ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    reason = Column(String(255))
    registered = Column(DateTime, default=datetime.datetime.now)

    @staticmethod
    def perform(
            sender: User,
            receiver: User,
            amount: int,
            reason: str = None
    ) -> "Transaction":

        if amount < 0:
            raise ValueError("No negative transactions!")
        elif amount == 0:
            raise ValueError("Empty transaction!")
        if sender is receiver:
            raise ValueError("Sender equals receiver!")

        sender.balance -= amount
        receiver.balance += amount

        transaction = Transaction(sender=sender.id, receiver=receiver.id, amount=amount, reason=reason)
        SESSION.add(transaction)
        SESSION.commit()
        return transaction

    @staticmethod
    def get(self, user: User, length: int = None) -> List["Transaction"]:
        query = SESSION.query(Transaction).filter(
            or_(
                Transaction.sender == user.id,
                Transaction.receiver == user.id
            )
        )
        if length is None:
            return query.all()
        else:
            return query.slice(0, length)


# Setup db
_ENGINE = create_engine("sqlite:///test.db", echo=True)
SESSION = sessionmaker(bind=_ENGINE)()
_Base.metadata.create_all(_ENGINE)
User.get_or_create("", name="Community", username="Community", active=True)
