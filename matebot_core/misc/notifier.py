"""
MateBot API callback library to handle remote push notifications
"""

import asyncio
import logging
import threading
from queue import Queue
from typing import ClassVar, List, Optional, Tuple

import aiohttp

from ..persistence import models


class Callback:
    """
    Collection of class methods to easily trigger push notifications (HTTP callbacks)
    """

    loop: ClassVar[Optional[asyncio.AbstractEventLoop]] = None
    queue: ClassVar[Queue[Tuple[List[str], List[Tuple[str, str]]]]] = Queue()
    logger: ClassVar[logging.Logger] = logging.getLogger("callback")
    thread: ClassVar[Optional[threading.Thread]] = None

    @classmethod
    async def _get(cls, paths: List[str], clients: List[Tuple[str, str]]):
        async with aiohttp.ClientSession() as session:
            for path in paths:
                if path.startswith("/"):
                    path = path[1:]

                for client in clients:
                    base, app = client
                    url = base + ("/" if not base.endswith("/") else "") + path

                    try:
                        response = await session.get(url, timeout=aiohttp.ClientTimeout(total=2))
                        if response.status != 200:
                            cls.logger.warning(
                                f"Callback for {app!r} at {url!r} failed with response code {response.status!r}."
                            )
                    except aiohttp.ClientConnectionError as exc:
                        cls.logger.info(
                            f"{type(exc).__name__} during callback request for {app!r} "
                            f"at {url!r}: {', '.join(map(repr, exc.args))}"
                        )
                    except asyncio.TimeoutError:
                        cls.logger.warning(f"Timeout while trying 'GET {url}' of app {app}")

    @classmethod
    async def _run_worker(cls):
        while True:
            item = cls.queue.get(block=True, timeout=30)
            cls.logger.debug(f"Handling callback item {item} ...")
            await cls._get(item[0], item[1])

    @classmethod
    def _run_thread(cls):
        threading.Thread(target=lambda: asyncio.run(cls._run_worker()), daemon=True).start()

    @classmethod
    async def created(cls, model_name: str, model_id: int, clients: List[models.Callback]):
        if not cls.thread:
            cls._run_thread()
        cls.queue.put(([f"create/{model_name.lower()}/{model_id}"], [(c.base, c.app.name) for c in clients]))

    @classmethod
    async def updated(cls, model_name: str, model_id: int, clients: List[models.Callback]):
        if not cls.thread:
            cls._run_thread()
        cls.queue.put(([f"update/{model_name.lower()}/{model_id}"], [(c.base, c.app.name) for c in clients]))

    @classmethod
    async def deleted(cls, model_name: str, model_id: int, clients: List[models.Callback]):
        if not cls.thread:
            cls._run_thread()
        cls.queue.put(([f"delete/{model_name.lower()}/{model_id}"], [(c.base, c.app.name) for c in clients]))
