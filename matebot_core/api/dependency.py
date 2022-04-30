"""
MateBot API dependency library
"""

import logging
from typing import Generator, Optional, Tuple

import sqlalchemy.exc
import fastapi.datastructures
from fastapi import BackgroundTasks, Depends, Request, Response
from fastapi.security import OAuth2PasswordBearer
from jose import jwt
from sqlalchemy.orm import Session

from . import base
from ..persistence import database, models
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
        raise
    except sqlalchemy.exc.SQLAlchemyError as exc:
        logger.exception(f"{type(exc).__name__}: {str(exc)}")
        session.rollback()
        raise
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


async def check_auth_token(token: str = Depends(OAuth2PasswordBearer(tokenUrl="login"))) -> Tuple[str, str, int]:
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
        expiration = int(payload.get("exp", 0))
        if username is None or expiration <= 0:
            raise credentials_exception
        return token, username, expiration
    except (jwt.JWTError, ValueError) as exc:
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
            auth_check: Tuple[str, str, int] = Depends(check_auth_token)
    ):
        super().__init__(request, response, session)
        self.tasks: BackgroundTasks = tasks
        self._token, self._requesting_app_name, self._token_expiration = auth_check
        self.headers: fastapi.datastructures.Headers = request.headers
        self.session: sqlalchemy.orm.Session = session
        self._config: Optional[Settings] = None

        target_apps = session.query(models.Application).filter_by(name=self._requesting_app_name).all()
        if len(target_apps) != 1:
            raise base.APIException(status_code=500, detail=self._token, message="Token owner couldn't be determined")
        self.origin_app: models.Application = target_apps[0]

    @property
    def config(self) -> Settings:
        if self._config is None:
            self._config = Settings()
        return self._config
