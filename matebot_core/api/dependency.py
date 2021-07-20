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
    TODO
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
