import logging
import datetime
from typing import List, Union

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Sequence, DateTime, ForeignKey
from sqlalchemy.orm import sessionmaker
from sqlalchemy.sql.expression import or_
from sqlalchemy.sql import func

from mate_bot.parsing.util import Representable


logger = logging.getLogger("state")

_Base = declarative_base()


class User(_Base, Representable):
    __tablename__ = "users"

    id = Column(Integer, Sequence("user_id_seq"), primary_key=True)
    matrix_id = Column(String(255), unique=True)
    display_name = Column(String(255))
    balance = Column(Integer, default=0)
    permission = Column(Boolean, default=False)
    active = Column(Boolean, default=False)
    created = Column(DateTime, default=datetime.datetime.now)
    accessed = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)

    @property
    def external(self):
        return SESSION.query(External).filter_by(external=self.id).count() == 1

    @property
    def creditor(self) -> "User":
        try:
            return User(SESSION.query(External).filter_by(external=self.id).first().internal)
        except Exception as err:
            logger.debug(str(err))
            return None

    @property
    def debtors(self) -> List["User"]:
        return list(map(User.get, SESSION.query(External).filter_by(internal=self.id).all()))

    def __str__(self):
        if self.display_name:
            return self.display_name
        else:
            return self.matrix_id

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
    def get(id_: Union[str, int]) -> "User":
        if isinstance(id_, str):
            query = SESSION.query(User).filter_by(matrix_id=id_)
        else:
            query = SESSION.query(User).filter_by(id=id_)

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
        return SESSION.query(User).filter_by(id=1).first()

    @staticmethod
    def put_blame() -> List["User"]:
        max_ = SESSION.query(func.max(User.balance)).first()[0]
        return SESSION.query(User).filter_by(balance=max_).all()


class Transaction(_Base):
    __tablename__ = "transactions"

    id = Column(Integer, Sequence("transaction_id_seq"), primary_key=True)
    sender = Column(ForeignKey("users.id"), nullable=False)
    receiver = Column(ForeignKey("users.id"), nullable=False)
    amount = Column(Integer, nullable=False)
    reason = Column(String(255))
    registered = Column(DateTime, default=datetime.datetime.now)

    def __str__(self):
        sender = str(User.get(self.sender))
        receiver = str(User.get(self.receiver))
        return f"{self.registered}: {self.amount/100:>+6.2f}: {sender} >> {receiver} :: {self.reason}"

    @staticmethod
    def perform(
            sender: User,
            receiver: User,
            amount: int,
            reason: str = None
    ) -> "Transaction":

        logger.debug(f"A transaction of {amount} cents from {sender} to {receiver} is about to be performed.")

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

        logger.info(f"{sender} just paid {receiver} {amount} cents")

        return transaction

    @staticmethod
    def get(user: User, length: int = None) -> List["Transaction"]:
        logger.debug(f"A transaction history was requested by {user}")
        query = SESSION.query(Transaction).filter(
            or_(
                Transaction.sender == user.id,
                Transaction.receiver == user.id
            )
        )
        if length is None:
            return query.all()
        else:
            return query.slice(0, length).all()


class External(_Base):
    __tablename__ = "externals"

    id = Column(Integer, Sequence("transaction_id_seq"), primary_key=True)
    internal = Column(ForeignKey("users.id"), nullable=False)
    external = Column(ForeignKey("users.id"), nullable=False, unique=True)
    changed = Column(DateTime, default=datetime.datetime.now, onupdate=datetime.datetime.now)


# Setup db
_ENGINE = create_engine("sqlite:///test.db", echo=logger.level == logging.DEBUG)
SESSION = sessionmaker(bind=_ENGINE)()
_Base.metadata.create_all(_ENGINE)
User.get_or_create("", display_name="Community", active=True)
