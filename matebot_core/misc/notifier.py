"""
MateBot API callback library to handle remote push notifications
"""

import asyncio
import logging
import datetime
import threading
from queue import Empty, Queue
from typing import ClassVar, List, Optional

import aiohttp

from ..api import dependency
from ..persistence import models
from .. import schemas


EVENT_QUEUE_WAIT_TIME = 3
EVENT_QUEUE_BUFFER_TIME = 0.25


class Callback:
    """
    Collection of class methods to easily trigger push notifications (HTTP callbacks)
    """

    queue: ClassVar[Queue[schemas.Event]] = Queue()
    logger: ClassVar[logging.Logger] = logging.getLogger(__name__)
    shutdown_event: ClassVar[threading.Event] = threading.Event()
    _thread: ClassVar[Optional[threading.Thread]] = None
    _session: ClassVar[Optional[aiohttp.ClientSession]] = None

    @classmethod
    def created(cls, *args, **kwargs):
        cls.logger.warning(f"Backward-incompatibility in Callback.created; args={args}; kwargs={kwargs}")

    @classmethod
    def updated(cls, *args, **kwargs):
        cls.logger.warning(f"Backward-incompatibility in Callback.updated; args={args}; kwargs={kwargs}")

    @classmethod
    def deleted(cls, *args, **kwargs):
        cls.logger.warning(f"Backward-incompatibility in Callback.deleted; args={args}; kwargs={kwargs}")

    @classmethod
    async def _publish_event(cls, callback: schemas.Callback, events: List[schemas.Event]):
        events_notification = schemas.EventsNotification(events=events, number=len(events))
        try:
            response = await cls._session.post(
                callback.url,
                json=events_notification.dict(),  # TODO: maybe need some other conversion
                timeout=aiohttp.ClientTimeout(total=2),
                headers=callback.shared_secret and {"Authorization": f"Bearer {callback.shared_secret}"}
            )
            if response.status != 200:
                cls.logger.warning(f"Callback for {callback.url!r} failed with response code {response.status!r}.")
        except aiohttp.ClientConnectionError as exc:
            cls.logger.info(
                f"{type(exc).__name__} during callback to 'POST {callback.url}' for {callback.application_id} "
                f"with the following arguments: {', '.join(map(repr, exc.args))}"
            )
        except asyncio.TimeoutError:
            cls.logger.warning(f"Timeout while trying 'POST {callback.url}' of app {callback.application_id}")

    @classmethod
    async def _run_worker(cls):
        if cls._session is None:
            cls._session = aiohttp.ClientSession()
        while not cls.shutdown_event.is_set():
            try:
                events = [cls.queue.get(block=True, timeout=EVENT_QUEUE_WAIT_TIME)]
            except Empty:
                continue
            try:
                events.append(cls.queue.get(block=True, timeout=EVENT_QUEUE_BUFFER_TIME))
            except Empty:
                pass
            callbacks = []
            for session in dependency.get_session():
                callbacks = [obj.schema for obj in session.query(models.Callback).all()]
            cls.logger.debug(f"Handling {len(events)} events '{events}' for {len(callbacks)} callbacks ...")
            for c in callbacks:
                await cls._publish_event(c, events)
        cls.logger.info("Stopped event notifier thread")

    @classmethod
    def _run_thread(cls):
        if not cls._thread:
            if cls._thread and cls._thread.is_alive():
                cls.logger.error("Re-starting thread while old thread is still alive!")
                cls.logger.debug(f"Enumerating threads: {threading.enumerate()}")
            cls._thread = threading.Thread(target=lambda: asyncio.run(cls._run_worker()), daemon=False)
            cls._thread.start()
        cls.logger.debug(f"Enumerating threads: {threading.enumerate()}")

    @classmethod
    def push(cls, event: schemas.EventType, data: Optional[dict] = None):
        cls._run_thread()
        cls.queue.put(schemas.Event(event=event, timestamp=int(datetime.datetime.now().timestamp()), data=data or {}))
