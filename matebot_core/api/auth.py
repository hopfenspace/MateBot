"""
Authentication helper library for the core REST API
"""

import hashlib
import secrets
import datetime

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import base, helpers
from ..persistence import models


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha512(
        hashlib.sha512(password.encode("UTF-8")).digest() + salt.encode("UTF-8")
    ).hexdigest()


async def check_app_credentials(application: str, password: str, session: Session) -> bool:
    apps = await helpers.return_all(models.Application, session, name=application)
    if len(apps) != 1:
        return False
    app = apps[0]
    if not getattr(app, "password", None):
        return False
    salted_hash = hash_password(password, app.password.salt)
    return secrets.compare_digest(salted_hash, app.password.passwd)


def create_access_token(username: str, expiration_minutes: int = 120) -> str:
    return jwt.encode(
        {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expiration_minutes),
            "iat": datetime.datetime.utcnow(),
            "username": username
        },
        base.runtime_key,
        algorithm=jwt.ALGORITHMS.HS256
    )
