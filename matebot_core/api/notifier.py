"""
MateBot API callback library to handle remote push notifications
"""

import logging
from typing import ClassVar, List, Optional

import aiohttp
import sqlalchemy.orm

from ..persistence import models


class Callback:
    """
    Collection of class methods to easily trigger push notifications (HTTP callbacks)
    """

    client_session: ClassVar[Optional[aiohttp.ClientSession]] = None

    @classmethod
    def _init(cls):
        if cls.client_session is None:
            cls.client_session = aiohttp.ClientSession()

    @classmethod
    async def shutdown(cls):
        if cls.client_session is not None:
            await cls.client_session.close()
            cls.client_session = None

    @classmethod
    async def _get(cls, paths: List[str], session: sqlalchemy.orm.Session, logger: logging.Logger):
        cls._init()
        clients = session.query(models.Callback).all()
        for p in paths:
            if p.startswith("/"):
                p = p[1:]
            for client in clients:
                url = client.base + ("/" if not client.base.endswith("/") else "") + p
                try:
                    response = await cls.client_session.get(url)
                    if response.status != 200:
                        logger.info(
                            f"Callback for {getattr(client.app, 'name', '<unknown app>')!r} "
                            f"at {url!r} failed with response code {response.status!r}."
                        )
                except aiohttp.ClientConnectionError as exc:
                    logger.info(
                        f"{type(exc).__name__} during callback request for "
                        f"{getattr(client.app, 'name', '<unknown app>')!r} "
                        f"at {url!r}: {', '.join(map(repr, exc.args))}"
                    )

    @classmethod
    async def refreshed(cls, logger: logging.Logger, session: sqlalchemy.orm.Session):
        await cls._get(["refresh"], session, logger)

    @classmethod
    async def created(
            cls,
            model_name: str,
            model_id: int,
            logger: logging.Logger,
            session: sqlalchemy.orm.Session
    ):
        await cls._get(["refresh", f"create/{model_name.lower()}/{model_id}"], session, logger)

    @classmethod
    async def updated(
            cls,
            model_name: str,
            model_id: int,
            logger: logging.Logger,
            session: sqlalchemy.orm.Session
    ):
        await cls._get(["refresh", f"update/{model_name.lower()}/{model_id}"], session, logger)

    @classmethod
    async def deleted(
            cls,
            model_name: str,
            model_id: int,
            logger: logging.Logger,
            session: sqlalchemy.orm.Session
    ):
        await cls._get(["refresh", f"delete/{model_name.lower()}/{model_id}"], session, logger)
