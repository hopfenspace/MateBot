"""
MateBot unit tests for the whole API in certain user actions
"""

import random
import unittest
import threading
from typing import Callable, ClassVar, List

import uvicorn

from matebot_core import settings as _settings
from matebot_core.api.api import create_app

from . import database


class _BaseAPITests(unittest.TestCase):
    cleanup_actions: ClassVar[List[Callable[[], None]]] = []
    server_port: int
    server_thread: threading.Thread

    def setUp(self) -> None:
        self.server_port = random.randint(10000, 64000)
        db_url, cleanup = database.get_database_url()
        type(self).cleanup_actions.append(cleanup)

        settings = _settings.Settings()
        settings.database.connection = db_url

        app = create_app(
            settings=settings,
            configure_logging=False,
            configure_static_docs=False
        )

        def run_server():
            uvicorn.run(
                app,  # noqa
                port=self.server_port,
                host="127.0.0.1",
                debug=True,
                workers=1,
                log_level="debug",
                access_log=True
            )

        self.server_thread = threading.Thread(target=run_server, daemon=True)
        self.server_thread.start()

    @classmethod
    def tearDownClass(cls) -> None:
        for f in cls.cleanup_actions:
            f()


class WorkingAPITests(_BaseAPITests):
    pass


class FailingAPITests(_BaseAPITests):
    pass


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for cls in [WorkingAPITests, FailingAPITests]:
        for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
            suite.addTest(cls(fixture))
    return suite


if __name__ == '__main__':
    unittest.main()
