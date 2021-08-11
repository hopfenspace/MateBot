"""
MateBot unit tests for the whole API in certain user actions
"""

import os
import random
import unittest
import threading
from typing import Iterable, Mapping, Optional, Tuple, Type, Union

import uvicorn
import pydantic
import requests

from matebot_core import settings as _settings
from matebot_core.schemas import config as _config
from matebot_core.api.api import create_app

from . import utils


class _BaseAPITests(utils.BaseTest):
    server_port: int
    server_thread: threading.Thread

    @property
    def server(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/"

    def assertQuery(
            self,
            endpoint: Tuple[str, str],
            status_code: Union[int, Iterable[int]] = 200,
            json: Optional[Union[dict, pydantic.BaseModel]] = None,
            headers: Optional[dict] = None,
            r_headers: Optional[Union[Mapping, Iterable]] = None,
            r_schema: Optional[Union[pydantic.BaseModel, Type[pydantic.BaseModel]]] = None,
            **kwargs
    ) -> requests.Response:
        """
        Do a query to the specified endpoint and return the response

        Besides also carrying the optional JSON data, headers and other keyword arguments,
        this function asserts that the response has the specified status code. Furthermore,
        the optional asserted response headers and asserted response schema can be used,
        where the headers are either an iterable to only assert certain keys or a mapping
        to also assert values, and the schema is either a schema class or an instance
        thereof (in the later case, the values will be compared to the response, too).

        :param endpoint: tuple of the method and the path of that endpoint
        :param status_code: asserted status code(s) of the final server's response
        :param json: optional dictionary or model holding the request data
        :param headers: optional set of headers to sent in the request
        :param r_headers optional set of headers which are asserted in the response
        :param r_schema: optional class or instance of a response schema to be asserted
        :param kwargs: dict of any further keyword arguments, passed to ``requests.request``
        :return: response to the requested resource
        """

        method, path = endpoint
        if path.startswith("/"):
            path = path[1:]
        if isinstance(json, pydantic.BaseModel):
            json = json.dict()

        response = requests.request(
            method.upper(),
            self.server + path,
            json=json,
            headers=headers,
            **kwargs
        )

        if isinstance(status_code, int):
            self.assertEqual(status_code, response.status_code)
        elif isinstance(status_code, Iterable):
            self.assertTrue(response.status_code in status_code)

        if r_headers is not None:
            for k in (r_headers if isinstance(r_headers, Iterable) else r_headers.keys()):
                self.assertIsNotNone(response.headers.get(k))
                if isinstance(r_headers, Mapping):
                    self.assertEqual(r_headers[k], response.headers.get(k))

        if r_schema and isinstance(r_schema, pydantic.BaseModel):
            r_model = type(r_schema)(**response.json())
            self.assertEqual(r_schema, r_model)
        elif r_schema and isinstance(r_schema, type) and issubclass(r_schema, pydantic.BaseModel):
            self.assertTrue(r_schema(**response.json()))

        return response

    def setUp(self) -> None:
        super().setUp()
        self.server_port = random.randint(10000, 64000)

        config = _config.CoreConfig(**_settings._get_default_config())
        config.database.echo = False
        config.database.connection = self.database_url
        config.server.port = self.server_port
        with open("config.json", "w") as f:
            f.write(config.json())
        self.cleanup_actions.append(
            lambda: os.path.exists("config.json") and os.remove("config.json")
        )

        app = create_app(
            settings=_settings.Settings(),
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


class WorkingAPITests(_BaseAPITests):
    def test_basic_endpoints_and_redirects_to_docs(self):
        self.assertQuery(
            ("GET", "/"),
            [302, 303, 307],
            r_headers={"Location": "/docs"},
            allow_redirects=False
        )

        self.assertEqual(self.server + "docs", self.assertQuery(("GET", "/")).url)
        self.assertEqual(1, len(self.assertQuery(("GET", "/")).history))
        self.assertEqual(
            self.assertQuery(("GET", "/")).content,
            self.assertQuery(("GET", "/docs")).content
        )
        self.assertQuery(("GET", "/openapi.json"), r_headers={"Content-Type": "application/json"})


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
