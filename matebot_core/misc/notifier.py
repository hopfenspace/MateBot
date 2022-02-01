"""
MateBot API callback library to handle remote push notifications
"""

import asyncio
import logging
from typing import List

import aiohttp

from ..persistence import models


class Callback:
    """
    Collection of class methods to easily trigger push notifications (HTTP callbacks)
    """

    @classmethod
    async def _get(cls, paths: List[str], clients: List[models.Callback], logger: logging.Logger):
        async with aiohttp.ClientSession() as session:
            for p in paths:
                if p.startswith("/"):
                    p = p[1:]
                for client in clients:
                    url = client.base + ("/" if not client.base.endswith("/") else "") + p
                    try:
                        response = await session.get(url, timeout=aiohttp.ClientTimeout(total=2))
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
                    except asyncio.TimeoutError:
                        logger.warning(f"Timeout while trying 'GET {url}'")

    @classmethod
    async def created(
            cls,
            model_name: str,
            model_id: int,
            logger: logging.Logger,
            clients: List[models.Callback]
    ):
        await cls._get([f"create/{model_name.lower()}/{model_id}"], clients, logger)

    @classmethod
    async def updated(
            cls,
            model_name: str,
            model_id: int,
            logger: logging.Logger,
            clients: List[models.Callback]
    ):
        await cls._get([f"update/{model_name.lower()}/{model_id}"], clients, logger)

    @classmethod
    async def deleted(
            cls,
            model_name: str,
            model_id: int,
            logger: logging.Logger,
            clients: List[models.Callback]
    ):
        await cls._get([f"delete/{model_name.lower()}/{model_id}"], clients, logger)
