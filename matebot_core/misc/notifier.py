"""
MateBot API callback library to handle remote push notifications
"""

import asyncio
import logging
import datetime
import threading
from queue import Empty, Queue
from typing import ClassVar, Optional, Tuple

import aiohttp

from .. import schemas


class Callback:
    """
    Collection of class methods to easily trigger push notifications (HTTP callbacks)
    """

    loop: ClassVar[Optional[asyncio.AbstractEventLoop]] = None
    queue: ClassVar[Queue[Tuple[schemas.Callback, schemas.Event]]] = Queue()
    logger: ClassVar[logging.Logger] = logging.getLogger("callback")
    thread: ClassVar[Optional[threading.Thread]] = None
    session: aiohttp.ClientSession = aiohttp.ClientSession()

    @classmethod
    async def _publish_event(cls, callback: schemas.Callback, event: schemas.Event):
        try:
            response = await cls.session.post(
                callback.base,
                json=event.dict(),  # TODO: maybe need some other conversion
                timeout=aiohttp.ClientTimeout(total=2),
                headers={"Authorization": f"Bearer {callback.shared_secret}"}
            )
            if response.status != 200:
                cls.logger.warning(f"Callback for {callback.base!r} failed with response code {response.status!r}.")
        except aiohttp.ClientConnectionError as exc:
            cls.logger.info(
                f"{type(exc).__name__} during callback to 'POST {callback.base}' for {callback.application_id} "
                f"with the following arguments: {', '.join(map(repr, exc.args))}"
            )
        except asyncio.TimeoutError:
            cls.logger.warning(f"Timeout while trying 'POST {callback.base}' of app {callback.application_id}")

    @classmethod
    async def _run_worker(cls):
        while True:  # while event not set; see https://docs.aiohttp.org/en/stable/client_advanced.html#graceful-shutdown
            try:
                item = cls.queue.get(block=True, timeout=30)
            except Empty:
                continue
            callback, event = item
            cls.logger.debug(f"Handling callback {event} for {callback} ...")
            await cls._publish_event(callback, event)

    @classmethod
    def _run_thread(cls):
        if not cls.thread or not cls.thread.is_alive():
            cls.thread = threading.Thread(target=lambda: asyncio.run(cls._run_worker()), daemon=True)
            cls.thread.start()

    @classmethod
    def push(cls, event: schemas.EventType, data: Optional[dict] = None, callbacks: Optional[schemas.Callback] = None):
        cls._run_thread()
        for callback in (callbacks or []):
            cls.queue.put((callback, schemas.Event(event=event, timestamp=datetime.datetime.now(), data=data or {})))
