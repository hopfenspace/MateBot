"""
MateBot API dependency library
"""

from typing import Generator, Optional

import sqlalchemy.exc
from fastapi import Request, Response, Header, Depends
from sqlalchemy.orm import Session

from . import etag
from ..persistence import database


def _get_session() -> Generator[Session, None, bool]:
    """
    Return a generator to handle database sessions gracefully
    """

    session = database.get_new_session()
    try:
        yield session
        session.flush()
    except sqlalchemy.exc.SQLAlchemyError:
        session.rollback()
        session.close()
        raise
    finally:
        session.close()
    return True


class LocalRequestData:
    """
    Collection of core dependencies used by all path operations

    This class stores references to various important objects that
    will almost certainly be used by request handlers (path operations).
    Note that any dependency added here will be added to the OpenAPI
    definition, if it refers to a Query, Header, Path or Cookie.

    Just add a single dependency for this class to your path operation
    to be able to use its attributes in a well-defined manner:

    .. code-block:: python3

        @app.get("/user")
        def get_user(local: LocalRequestData = Depends(LocalRequestData)):
            ...

    """

    def __init__(
            self,
            request: Request,
            response: Response,
            session: Session = Depends(_get_session),
            match: Optional[str] = Header(None, alias="If-Match"),
            match_none: Optional[str] = Header(None, alias="If-None-Match")
    ):
        self.request = request
        self.response = response
        self.headers = request.headers
        self.entity = etag.Entity(request)
        self.match = match
        self.match_none = match_none
        self.session = session
