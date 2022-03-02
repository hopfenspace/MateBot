"""
MateBot API dependency library
"""

import logging
from typing import Generator, Optional

import sqlalchemy.exc
from fastapi import BackgroundTasks, Depends, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from . import base
from ..persistence import database
from ..settings import Settings


def get_session() -> Generator[Session, None, bool]:
    """
    Return a generator to handle database sessions gracefully
    """

    logger = logging.getLogger(__name__)
    session = database.get_new_session()

    try:
        yield session
        session.flush()
    except sqlalchemy.exc.DBAPIError as exc:
        details = exc.statement.replace("\n", "")
        logger.exception(f"{type(exc).__name__}: {', '.join(exc.args)} @ {details!r}")
        session.rollback()
        raise base.APIException(status_code=500, detail="", repeat=False, message="Unexpected error") from exc
    except sqlalchemy.exc.SQLAlchemyError as exc:
        logger.exception(f"{type(exc).__name__}: {str(exc)}")
        session.rollback()
        raise base.APIException(status_code=500, detail="", repeat=False, message="Unexpected error") from exc
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()
    return True


class MinimalRequestData:
    """
    Collection of minimal dependencies used only for internal functionalities
    """

    def __init__(
            self,
            request: Request,
            response: Response,
            session: Session = Depends(get_session)
    ):
        self.request = request
        self.response = response
        self.headers = request.headers
        self.session = session

        self._config: Optional[Settings] = None

    @property
    def config(self) -> Settings:
        if self._config is None:
            self._config = Settings()
        return self._config


async def check_auth_token(token: str = Depends(OAuth2PasswordBearer(tokenUrl="login"))):
    credentials_exception = base.APIException(
        status_code=401,
        detail=f"token={token!r}",
        message="Failed to validate token successfully",
        headers={"WWW-Authenticate": "Bearer"}
    )

    try:
        payload = jwt.decode(
            token,
            base.runtime_key,
            algorithms=[jwt.ALGORITHMS.HS256],
            options={"require_exp": True, "require_iat": True}
        )
        username = payload.get("sub", None)
        if username is None:
            raise credentials_exception
    except jwt.JWTError as exc:
        raise credentials_exception from exc


class LocalRequestData(MinimalRequestData):
    """
    Collection of core dependencies used by all path operations

    This class stores references to various important objects that
    will almost certainly be used by request handlers (path operations).
    Note that any dependency added here will be added to the OpenAPI
    definition, if it refers to a Query, Header, Path or Cookie.
    """

    def __init__(
            self,
            request: Request,
            response: Response,
            tasks: BackgroundTasks,
            session: Session = Depends(get_session),
            token: str = Depends(check_auth_token)
    ):
        super().__init__(request, response, session)
        self.tasks = tasks
        self._token = token
        self.headers = request.headers
        self.session = session
        self._config: Optional[Settings] = None

    @property
    def config(self) -> Settings:
        if self._config is None:
            self._config = Settings()
        return self._config
