"""
Authentication helper library for the core REST API
"""

import hashlib
import datetime

from jose import JWTError, jwt
from sqlalchemy.orm import Session

from . import base, helpers


def hash_password(password: str, salt: str) -> str:
    return hashlib.sha512(
        hashlib.sha512(password.encode("UTF-8")).digest() + salt.encode("UTF-8")
    ).hexdigest()


def create_access_token(username: str, expiration_minutes: int = 120) -> str:
    return jwt.encode(
        {
            "exp": datetime.datetime.utcnow() + datetime.timedelta(minutes=expiration_minutes),
            "iat": datetime.datetime.utcnow(),
            "username": username
        },
        base.runtime_key
    )
