"""
Authentication helper library for the core REST API
"""

import hashlib
import secrets
import datetime

from jose import jwt
from sqlalchemy.orm import Session

from . import base
from ..persistence import models
from ..settings import Settings


def hash_password(password: str, salt: str) -> str:
    h = hashlib.sha512(hashlib.sha512(password.encode("UTF-8")).digest() + salt.encode("UTF-8"))
    for _ in range(Settings().server.password_iterations):
        h = hashlib.sha512(h.digest())
    return h.hexdigest()


async def check_app_credentials(application: str, password: str, session: Session) -> bool:
    apps = session.query(models.Application).filter_by(name=application).all()
    if len(apps) != 1:
        return False
    app = apps[0]
    if not getattr(app, "password", None):
        return False
    salted_hash = hash_password(password, app.salt)
    return secrets.compare_digest(salted_hash, app.password)


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
