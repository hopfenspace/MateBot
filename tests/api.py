"""
MateBot unit tests for the whole API in certain user actions
"""

import os
import random
import unittest
import threading
from typing import Callable, ClassVar, List

import uvicorn
import requests

from matebot_core import settings as _settings
from matebot_core.schemas import config as _config
from matebot_core.api.api import create_app

from . import database


class _BaseAPITests(unittest.TestCase):
    cleanup_actions: ClassVar[List[Callable[[], None]]] = []
    server_port: int
    server_thread: threading.Thread

    @property
    def server(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/"

    def setUp(self) -> None:
        self.server_port = random.randint(10000, 64000)
        db_url, cleanup = database.get_database_url()
        type(self).cleanup_actions.append(cleanup)

        config = _config.CoreConfig(**_settings._get_default_config())
        config.database.connection = db_url
        config.server.port = self.server_port
        with open("config.json", "w") as f:
            print("f", f.write(config.json()))

        settings = _settings.Settings()

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

        def wait_for_server():
            try:
                requests.get(self.server)
            except requests.exceptions.ConnectionError:
                self.server_thread.join(0.05)
                wait_for_server()

        wait_for_server()

    def tearDown(self) -> None:
        if os.path.exists("config.json"):
            os.remove("config.json")

    @classmethod
    def tearDownClass(cls) -> None:
        for f in cls.cleanup_actions:
            f()


class WorkingAPITests(_BaseAPITests):
    def test_basic_endpoints_and_redirects_to_docs(self):
        response = requests.get(self.server, allow_redirects=False)
        self.assertEqual(self.server, response.url)
        self.assertEqual(307, response.status_code)
        self.assertEqual("/docs", response.headers.get("Location"))

        response_root = requests.get(self.server)
        self.assertEqual(self.server + "docs", response_root.url)
        self.assertEqual(200, response_root.status_code)
        self.assertEqual(1, len(response_root.history))

        response_docs = requests.get(self.server + "docs")
        self.assertEqual(200, response_docs.status_code)
        self.assertEqual(response_docs.content, response_root.content)

        response_openapi = requests.get(self.server + "openapi.json")
        self.assertEqual(200, response_openapi.status_code)
        self.assertEqual("application/json", response_openapi.headers.get("Content-Type"))


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
