"""
MateBot database bindings and functions using sqlalchemy
"""

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine as _Engine
from sqlalchemy.orm import declarative_base, sessionmaker


# TODO: move to the config file to allow other databases as well
SQLALCHEMY_DATABASE_URL = "sqlite:///./database.db"

Engine: _Engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}  # required for sqlite only
)

Base = declarative_base()
get_new_session = sessionmaker(autocommit=False, autoflush=False, bind=Engine)
