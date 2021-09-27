"""
MateBot API dependency library
"""

import logging
from typing import Generator, Optional

import sqlalchemy.exc
from fastapi import BackgroundTasks, Depends, Request, Response
from sqlalchemy.orm import Session

from . import auth, base, etag
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
        logger.error(f"{type(exc).__name__}: {', '.join(exc.args)} @ {details!r}")
        session.rollback()
        session.close()
        raise
    except sqlalchemy.exc.SQLAlchemyError as exc:
        logger.error(f"{type(exc).__name__}: {str(exc)}")
        session.rollback()
        session.close()
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


class LocalRequestData(MinimalRequestData):
    """
    Collection of core dependencies used by all path operations

    This class stores references to various important objects that
    will almost certainly be used by request handlers (path operations).
    Note that any dependency added here will be added to the OpenAPI
    definition, if it refers to a Query, Header, Path or Cookie.

    Just add a single dependency for this class to your path operation
    to be able to use its attributes in a well-defined manner. It also
    supports the attachment of the ``ETag`` header as well as specific
    extra headers to the response using just one additional method call:

    .. code-block:: python3

        @app.get("/user")
        def get_user(local: LocalRequestData = Depends(LocalRequestData)):
            ...
            return local.attach_headers(model)

    """

    def __init__(
            self,
            request: Request,
            response: Response,
            tasks: BackgroundTasks,
            session: Session = Depends(get_session),
            token: str = Depends(auth.check_auth)
    ):
        super().__init__(request, response, session)
        self.tasks = tasks
        self.entity = etag.ETag(request)
        self._token = token

    def attach_headers(self, model: base.ModelType, **kwargs) -> base.ModelType:
        """
        Attach the specified headers (excl. ETag) to the response and return the model
        """

        for k in kwargs:
            if k.lower() != "etag":
                self.response.headers.append(k, kwargs[k])
        self.entity.add_header(self.response, model)
        return model
