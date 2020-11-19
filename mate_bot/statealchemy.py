import datetime

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Column, Integer, String, Boolean, Sequence, DateTime
from sqlalchemy.orm import sessionmaker

from parsing.util import Representable


_Base = declarative_base()


class MateBotUser(_Base, Representable):
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

    @staticmethod
    def new(matrix_id: str, **kwargs) -> "MateBotUser":
        user = MateBotUser(matrix_id=matrix_id, **kwargs)
        SESSION.add(user)
        SESSION.commit()
        return user

    @staticmethod
    def get(matrix_id: str) -> "MateBotUser":
        query = SESSION.query(MateBotUser).filter_by(matrix_id=matrix_id)
        count = query.count()
        if count == 1:
            return query.first()
        elif count == 0:
            raise ValueError(f"No user with the id '{matrix_id}'")
        else:
            raise RuntimeError(f"The database is broken: Found more than one user with id '{matrix_id}'")

    @staticmethod
    def get_or_create(matrix_id: str, **kwargs) -> "MateBotUser":
        try:
            return MateBotUser.get(matrix_id)
        except ValueError:
            return MateBotUser.new(matrix_id, **kwargs)


# Setup db
_ENGINE = create_engine("sqlite:///test.db", echo=True)
SESSION = sessionmaker(bind=_ENGINE)()
_Base.metadata.create_all(_ENGINE)
MateBotUser.get_or_create("", name="Community", username="Community", active=True)
