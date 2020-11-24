import logging as _logging
import datetime as _datetime
from typing import (List as _List, Union as _Union, Optional as _Optional)

from sqlalchemy import create_engine as _create_engine
from sqlalchemy.ext.declarative import declarative_base as _declarative_base
from sqlalchemy import (Column as _Column, Integer as _Integer, String as _String, Boolean as _Boolean,
                        Sequence as _Sequence, DateTime as _DateTime, ForeignKey as _ForeignKey)
from sqlalchemy.orm import sessionmaker as _sessionmaker
from sqlalchemy.sql.expression import or_
from sqlalchemy.sql import func as _func


_logger = _logging.getLogger("state")

_Base = _declarative_base()


class User(_Base):
    __tablename__ = "users"

    id = _Column(_Integer, _Sequence("user_id_seq"), primary_key=True)
    matrix_id = _Column(_String(255), unique=True)
    display_name = _Column(_String(255))
    balance = _Column(_Integer, default=0)
    permission = _Column(_Boolean, default=False)
    active = _Column(_Boolean, default=False)
    created = _Column(_DateTime, default=_datetime.datetime.now)
    accessed = _Column(_DateTime, default=_datetime.datetime.now, onupdate=_datetime.datetime.now)

    @property
    def external(self) -> bool:
        return _SESSION.query(_External).filter_by(external=self.id).count() == 1

    @external.setter
    def external(self, is_external: bool):
        if is_external is False:
            _SESSION.delete(_SESSION.query(_External).filter_by(external=self.id).all())
        else:
            _SESSION.add(_External(external=self.id))
        _SESSION.commit()

    @property
    def creditor(self) -> _Optional["User"]:
        try:
            return User.get(_SESSION.query(_External).filter_by(external=self.id).first().internal)
        except Exception as err:
            _logger.debug(str(err))
            return None

    @creditor.setter
    def creditor(self, user: _Optional["User"]):
        if user is None:
            _SESSION.query(_External).filter_by(external=self.id).first().internal = None
        else:
            _SESSION.query(_External).filter_by(external=self.id).first().internal = user.id
        _SESSION.commit()

    @property
    def debtors(self) -> _List["User"]:
        return list(map(User.get, _SESSION.query(_External).filter_by(internal=self.id).all()))

    def __str__(self):
        if self.display_name:
            return self.display_name
        else:
            return self.matrix_id

    @staticmethod
    def push():
        _SESSION.commit()

    @staticmethod
    def new(matrix_id: str, **kwargs) -> "User":
        user = User(matrix_id=matrix_id, **kwargs)
        _SESSION.add(user)
        _SESSION.commit()
        return user

    @staticmethod
    def get(id_: _Union[str, int]) -> "User":
        if isinstance(id_, str):
            query = _SESSION.query(User).filter_by(matrix_id=id_)
        else:
            query = _SESSION.query(User).filter_by(id=id_)

        count = query.count()
        if count == 1:
            return query.first()
        elif count == 0:
            raise ValueError(f"No user with the id '{id_}'")
        else:
            raise RuntimeError(f"The database is broken: Found more than one user with id '{id_}'")

    @staticmethod
    def get_or_create(matrix_id: str, **kwargs) -> "User":
        try:
            return User.get(matrix_id)
        except ValueError:
            return User.new(matrix_id, **kwargs)

    @staticmethod
    def community_user():
        return _SESSION.query(User).filter_by(id=1).first()

    @staticmethod
    def put_blame() -> _List["User"]:
        min_ = _SESSION.query(_func.min(User.balance)).first()[0]
        return _SESSION.query(User).filter_by(balance=min_).all()


class Transaction(_Base):
    __tablename__ = "transactions"

    id = _Column(_Integer, _Sequence("transaction_id_seq"), primary_key=True)
    sender_id = _Column(_ForeignKey("users.id"), nullable=False)
    receiver_id = _Column(_ForeignKey("users.id"), nullable=False)
    amount = _Column(_Integer, nullable=False)
    reason = _Column(_String(255))
    date = _Column(_DateTime, default=_datetime.datetime.now)

    @property
    def sender(self) -> User:
        return User.get(self.sender_id)

    @property
    def receiver(self) -> User:
        return User.get(self.receiver_id)

    def as_exportable_dict(self):
        """
        Create a dict containing the relevant data as primitive types.

        :return: dict representing the transaction
        :rtype: dict
        """
        return {
            "sender": str(self.sender),
            "receiver": str(self.receiver),
            "amount": self.amount,
            "date": str(self.date)
        }

    def __str__(self):
        return f"{self.date}: {self.amount/100:>+6.2f}: {self.sender} >> {self.receiver} :: {self.reason}"

    @staticmethod
    def perform(
            sender: User,
            receiver: User,
            amount: int,
            reason: str = None
    ) -> "Transaction":

        _logger.debug(f"A transaction of {amount} cents from {sender} to {receiver} is about to be performed.")

        if amount < 0:
            raise ValueError("No negative transactions!")
        elif amount == 0:
            raise ValueError("Empty transaction!")
        if sender is receiver:
            raise ValueError("Sender equals receiver!")

        sender.balance -= amount
        receiver.balance += amount

        transaction = Transaction(sender_id=sender.id, receiver_id=receiver.id, amount=amount, reason=reason)
        _SESSION.add(transaction)
        _SESSION.commit()

        _logger.info(f"{sender} just paid {receiver} {amount} cents")

        return transaction

    @staticmethod
    def history(user: User, length: int = None) -> _List["Transaction"]:
        _logger.debug(f"A transaction history was requested by {user}")
        query = _SESSION.query(Transaction).filter(
            or_(
                Transaction.sender_id == user.id,
                Transaction.receiver_id == user.id
            )
        )
        if length is None:
            return query.all()
        else:
            return query.slice(0, length).all()


class _External(_Base):
    __tablename__ = "externals"

    id = _Column(_Integer, _Sequence("transaction_id_seq"), primary_key=True)
    internal = _Column(_ForeignKey("users.id"))
    external = _Column(_ForeignKey("users.id"), nullable=False, unique=True)
    changed = _Column(_DateTime, default=_datetime.datetime.now, onupdate=_datetime.datetime.now)


# Setup db
_ENGINE = _create_engine("sqlite:///test.db", echo=_logger.level == _logging.DEBUG)
_SESSION = _sessionmaker(bind=_ENGINE)()
_Base.metadata.create_all(_ENGINE)
User.get_or_create("", display_name="Community", active=True)
