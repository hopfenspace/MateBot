"""
Authentication helper library for the core REST API
"""

import datetime
from typing import Optional

from jose import jwt
from sqlalchemy.orm import Session
from argon2 import PasswordHasher, profiles

from . import base
from .. import schemas
from ..persistence import database, models
from ..settings import Settings


_password_check: Optional[PasswordHasher] = None


def hash_password(password: str) -> str:
    return _get_password_check().hash(password)


async def check_app_credentials(application: str, password: str, session: Session) -> bool:
    """
    Check the correctness of a password for a given application, raise some error otherwise
    """

    checker = _get_password_check()
    apps = session.query(models.Application).filter_by(name=application).all()
    if len(apps) > 1:
        raise ValueError(f"Multiple apps with name {application!r} found!")
    if len(apps) == 0:
        raise ValueError(f"Unknown app {application!r}!")
    app = apps[0]
    checker.verify(app.hashed_password, password)
    if checker.check_needs_rehash(app.hashed_password):
        app.hashed_password = checker.hash(password)
        with database.get_new_session() as s:
            s.add(app)
            s.commit()
    return True


def create_application(name: str, password: str) -> schemas.Application:
    with database.get_new_session() as session:
        app = models.Application(name=name, hashed_password=hash_password(password))
        session.add(app)
        session.commit()
        return app.schema


def _get_password_check() -> PasswordHasher:
    global _password_check
    if _password_check is not None:
        return _password_check
    config = Settings()
    if config.server.allow_weak_insecure_password_hashes:
        _password_check = PasswordHasher.from_parameters(profiles.CHEAPEST)
    else:
        _password_check = PasswordHasher.from_parameters(profiles.RFC_9106_LOW_MEMORY)
    return _password_check


def create_access_token(username: str, expiration_minutes: int = 120) -> str:
    return jwt.encode(
        {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expiration_minutes),
            "iat": datetime.datetime.utcnow(),
            "sub": username
        },
        base.runtime_key,
        algorithm=jwt.ALGORITHMS.HS256
    )
