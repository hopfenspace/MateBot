"""
MateBot unit tests for the whole API in certain user actions
"""

import os
import errno
import random
import threading
import http.server
import unittest as _unittest
from typing import Any, Iterable, List, Mapping, Optional, Tuple, Type, Union

import uvicorn
import pydantic
import requests

from matebot_core import settings as _settings
from matebot_core.schemas import config as _config
from matebot_core.api.api import create_app

from . import conf, utils


api_suite = _unittest.TestSuite()


def _tested(cls: Type):
    global api_suite
    for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
        api_suite.addTest(cls(fixture))
    return cls


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
            self.assertEqual(status_code, response.status_code, response.text)
        elif isinstance(status_code, Iterable):
            self.assertTrue(response.status_code in status_code, response.text)

        if r_headers is not None:
            for k in (r_headers if isinstance(r_headers, Iterable) else r_headers.keys()):
                self.assertIsNotNone(response.headers.get(k), response.headers)
                if isinstance(r_headers, Mapping):
                    self.assertEqual(r_headers[k], response.headers.get(k), response.headers)

        if r_schema and isinstance(r_schema, pydantic.BaseModel):
            r_model = type(r_schema)(**response.json())
            self.assertEqual(r_schema, r_model, response.json())
        elif r_schema and isinstance(r_schema, type) and issubclass(r_schema, pydantic.BaseModel):
            self.assertTrue(r_schema(**response.json()), response.json())

        return response

    def setUp(self) -> None:
        super().setUp()
        self.server_port = random.randint(10000, 64000)

        config = _config.CoreConfig(**_settings._get_default_config())
        config.database.echo = conf.SQLALCHEMY_ECHOING
        config.database.connection = self.database_url
        config.server.port = self.server_port
        with open("config.json", "w") as f:
            f.write(config.json())

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
                log_level="error",
                access_log=False
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
        super().tearDown()


@_tested
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


@_tested
class FailingAPITests(_BaseAPITests):
    pass


@_tested
class APICallbackTests(_BaseAPITests):
    callback_server: Optional[http.server.HTTPServer] = None
    callback_server_port: Optional[int] = None
    callback_server_thread: Optional[threading.Thread] = None
    callback_request_list: List[Tuple[str, str]] = []

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        request_list: List[Tuple[str, str]]

        def do_GET(self) -> None:  # noqa
            self.send_response(200)
            self.end_headers()
            self.request_list.append((self.command, self.path))

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

    def setUp(self) -> None:
        super().setUp()
        self.callback_request_list = []
        self.CallbackHandler.request_list = self.callback_request_list

        while True:
            try:
                self.callback_server_port = random.randint(10000, 64000)
                self.callback_server = http.server.HTTPServer(
                    ("127.0.0.1", self.callback_server_port),
                    self.CallbackHandler
                )
            except OSError as exc:
                if exc.errno == errno.EADDRINUSE:
                    continue
                raise
            else:
                break

        self.callback_server_thread = threading.Thread(
            target=self.callback_server.serve_forever,
            daemon=True
        )
        self.callback_server_thread.start()

    def test_callback_testing(self):
        self.assertListEqual([], self.callback_request_list)
        requests.get(f"http://localhost:{self.callback_server_port}/refresh")
        self.assertListEqual([("GET", "/refresh")], self.callback_request_list)
        requests.get(f"http://localhost:{self.callback_server_port}/refresh")
        requests.get(f"http://localhost:{self.callback_server_port}/refresh")
        requests.get(f"http://localhost:{self.callback_server_port}/refresh")
        self.assertTrue(all(map(lambda x: x == ("GET", "/refresh"), self.callback_request_list)))

        requests.get(f"http://localhost:{self.callback_server_port}/create/ballot/7")
        requests.get(f"http://localhost:{self.callback_server_port}/update/user/3")
        requests.get(f"http://localhost:{self.callback_server_port}/delete/vote/1")
        self.assertListEqual(
            [("GET", "/create/ballot/7"), ("GET", "/update/user/3"), ("GET", "/delete/vote/1")],
            self.callback_request_list[-3:]
        )
        self.assertTrue(all(map(lambda x: x[0] == "GET", self.callback_request_list)))

    def tearDown(self) -> None:
        self.callback_server.shutdown()
        super().tearDown()


if __name__ == '__main__':
    _unittest.main()
