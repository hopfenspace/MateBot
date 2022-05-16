"""
Helper functions to make writing unit tests for the MateBot core easier
"""

import os
import sys
import enum
import errno
import queue
import random
import string
import secrets
import unittest
import threading
import subprocess
import http.server
import urllib.parse
import json as _json
from typing import Any, Dict, Iterable, List, Mapping, Optional, Tuple, Type, Union

import pydantic
import requests
import sqlalchemy.orm
from sqlalchemy.engine import Engine as _Engine

from matebot_core import schemas as _schemas, settings as _settings
from matebot_core.api import auth
from matebot_core.persistence import database, models

from . import conf


class DatabaseType(enum.IntEnum):
    """
    Enum to simply determine which database is currently in use
    """

    SQLITE = enum.auto()
    MYSQL = enum.auto()


class BaseTest(unittest.TestCase):
    """
    A base class for unit tests which introduces simple setup and teardown of unit tests

    If a subclass needs special setup or teardown functionality, it **MUST**
    call the superclasses setup and teardown methods: the superclass setup
    method at the beginning of the subclass setup method, the superclass
    teardown method at the end of the subclass teardown method.
    """

    config_file: Optional[str] = None
    database_url: Optional[str] = None
    database_type: Optional[DatabaseType] = None
    _database_file: Optional[str] = None

    def setUp(self) -> None:
        self.config_file = f"config_{os.getpid()}_{secrets.token_hex(8)}.json"
        _settings.CONFIG_PATHS = [self.config_file]

        if conf.DATABASE_URL is not None:
            self.database_url = conf.DATABASE_URL
            for k in ["COMMAND_INITIALIZE_DATABASE", "COMMAND_CLEANUP_DATABASE"]:
                if not hasattr(conf, k):
                    print(
                        f"Mandatory config variable {k!r} not found in config file!",
                        file=sys.stderr
                    )
                    sys.exit(1)
                if getattr(conf, k) is None:
                    print(
                        f"{k!r} has not been set (value: None)! This config value "
                        "is mandatory for non-default databases. Any unittest may fail. "
                        "But if you really need no script(s), set it to an empty list.",
                        file=sys.stderr
                    )
                    sys.exit(1)

            if conf.COMMAND_INITIALIZE_DATABASE:
                subprocess.run(conf.COMMAND_INITIALIZE_DATABASE)

        else:
            self._database_file = conf.DATABASE_DEFAULT_FILE_FORMAT.format(
                os.getpid(),
                "".join([random.choice(string.ascii_lowercase) for _ in range(6)])
            )

            try:
                open(self._database_file, "wb").close()
                os.remove(self._database_file)
                self.database_url = conf.DATABASE_URL_FORMAT.format(self._database_file)

            except OSError as exc:
                self.database_url = conf.DATABASE_FALLBACK_URL
                self._database_file = None
                print(
                    f"{exc}: Falling back to in-memory database. This is not recommended!",
                    file=sys.stderr
                )

        if self.database_url.startswith("sqlite"):
            self.database_type = DatabaseType.SQLITE
        elif self.database_url.startswith("mysql"):
            self.database_type = DatabaseType.MYSQL
        elif self.database_url.startswith("mariadb"):
            self.database_type = DatabaseType.MYSQL
            print(
                f"The database URL {self.database_url!r} uses MariaDB scheme. "
                f"This may lead to problems. Use the plain MySQL scheme instead.",
                file=sys.stderr
            )
        else:
            print(
                f"Unknown scheme in URL {self.database_url!r}. Unittests may fail later.",
                file=sys.stderr
            )

    def tearDown(self) -> None:
        if conf.DATABASE_URL is not None and conf.COMMAND_CLEANUP_DATABASE:
            subprocess.run(conf.COMMAND_CLEANUP_DATABASE)

        elif self.database_url != conf.DATABASE_FALLBACK_URL and self._database_file:
            if os.path.exists(self._database_file):
                os.remove(self._database_file)

        if self.config_file and os.path.exists(self.config_file):
            os.remove(self.config_file)


class BasePersistenceTests(BaseTest):
    engine: _Engine
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        super().setUp()
        opts = {"echo": conf.SQLALCHEMY_ECHOING}
        if self.database_url.startswith("sqlite:"):
            opts = {"connect_args": {"check_same_thread": False}}
        self.engine = sqlalchemy.create_engine(self.database_url, **opts)
        self.session = sqlalchemy.orm.sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )()
        models.Base.metadata.create_all(bind=self.engine)

        config = _schemas.config.CoreConfig(**_settings.get_default_config())
        config.database.debug_sql = conf.SQLALCHEMY_ECHOING
        config.database.connection = self.database_url
        config.server.password_iterations = 1
        with open(self.config_file, "w") as f:
            f.write(config.json())

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        super().tearDown()

    @staticmethod
    def get_sample_users() -> List[models.User]:
        return [
            models.User(name="user1", balance=-42, external=True),
            models.User(name="user2", balance=51, external=False),
            models.User(name="user3", external=True),
            models.User(name="user4", balance=2, external=False),
            models.User(name="user5", permission=False, active=False, external=False, voucher_id=2),
            models.User(external=False),
            models.User(name="community", external=False, special=True, balance=2, permission=True)
        ]


class BaseAPITests(BaseTest):
    api_version_format: str = "/v{}"
    _latest_api_version: Optional[int] = None

    server_port: Optional[int] = None
    server_process: Optional[subprocess.Popen] = None

    auth: Optional[Tuple[str, str]] = None
    token: Optional[str] = None

    callback_server: Optional[http.server.HTTPServer] = None
    callback_server_port: Optional[int] = None
    callback_server_thread: Optional[threading.Thread] = None
    callback_request_list: "queue.Queue[Tuple[str, str]]" = queue.Queue()

    class CallbackHandler(http.server.BaseHTTPRequestHandler):
        request_list: "queue.Queue[Tuple[str, str]]"

        def do_HEAD(self) -> None:  # noqa
            self.send_response(200)
            self.end_headers()

        def do_GET(self) -> None:  # noqa
            self.send_response(200)
            self.end_headers()
            self.request_list.put((self.command, self.path))

        def log_message(self, fmt: str, *args: Any) -> None:
            pass

    @property
    def server(self) -> str:
        return f"http://127.0.0.1:{self.server_port}/"

    @property
    def callback_server_uri(self) -> str:
        return f"http://127.0.0.1:{self.callback_server_port}/"

    @property
    def latest_api_version(self) -> int:
        if not self._latest_api_version:
            response = requests.get(self.server + "versions")
            self._latest_api_version = int(response.json()["latest"])
        return self._latest_api_version

    def assertQuery(
            self,
            endpoint: Union[Tuple[str, str], Tuple[str, str, int]],
            status_code: Union[int, Iterable[int]] = 200,
            json: Optional[Union[dict, pydantic.BaseModel, List[Union[dict, pydantic.BaseModel]]]] = None,
            headers: Optional[dict] = None,
            r_none: bool = False,
            r_is_json: bool = True,
            r_headers: Optional[Union[Mapping, Iterable]] = None,
            r_schema: Optional[Union[pydantic.BaseModel, Type[pydantic.BaseModel]]] = None,
            r_schema_ignored_fields: Optional[List[str]] = None,
            skip_callbacks: Optional[int] = None,
            skip_callback_timeout: float = 0.025,
            recent_callbacks: Optional[List[Tuple[str, str]]] = None,
            callback_timeout: float = 0.5,
            no_version: bool = False,
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

        :param endpoint: tuple of the method, the path of the endpoint and the
            optional API version (uses the latest version if omitted by default)
        :param status_code: asserted status code(s) of the final server's response
        :param json: optional dictionary or model holding the request data
        :param headers: optional set of headers to sent in the request
        :param r_none: switch to expect no (=empty) result and skip all other response content checks
        :param r_is_json: switch to check that the response contains JSON data
        :param r_headers optional set of headers which are asserted in the response
        :param r_schema: optional class or instance of a response schema to be asserted
        :param r_schema_ignored_fields: list of ignored fields while checking a response with schema
        :param skip_callbacks: optional number of callback requests that will be dropped and
            not checked in the recent callback check later (no problem if the number is too high)
        :param skip_callback_timeout: maximal waiting time for the skip operation
        :param recent_callbacks: optional, unsorted list of the most recent ("rightmost") callbacks
            that arrived at the local callback HTTP server (which only works when its
            callback server URI has been registered in the API during the same unit test)
        :param callback_timeout: maximal waiting time until a callback request arrived
        :param no_version: don't add the latest version to the two-element endpoint definition
        :param kwargs: dict of any further keyword arguments, passed to ``requests.request``
        :return: response to the requested resource
        """

        if skip_callbacks is not None:
            while skip_callbacks > 0:
                try:
                    skip_callbacks -= 1
                    self.callback_request_list.get(timeout=skip_callback_timeout)
                except queue.Empty:
                    pass

        if len(endpoint) == 3:
            method, path, api_version = endpoint
        else:
            method, path = endpoint
            api_version = self.latest_api_version

        if path.startswith("/"):
            path = path[1:]
        if isinstance(json, list):
            json = [e if not isinstance(e, pydantic.BaseModel) else e.dict() for e in json]
        if isinstance(json, pydantic.BaseModel):
            json = json.dict()

        prefix = self.api_version_format.format(api_version)
        if prefix.startswith("/"):
            prefix = prefix[1:]
        if no_version:
            prefix = ""
        elif not prefix.endswith("/"):
            prefix += "/"
        headers = headers or {}
        headers.update({"Authorization": f"Bearer {self.token}"})
        response = requests.request(
            method.upper(),
            self.server + prefix + path,
            json=json,
            headers=headers,
            **kwargs
        )

        if isinstance(status_code, int):
            self.assertEqual(status_code, response.status_code, response.text)
        elif isinstance(status_code, Iterable):
            self.assertTrue(
                response.status_code in status_code,
                (response.text, response.status_code, status_code)
            )

        if r_headers is not None:
            for k in (r_headers if isinstance(r_headers, Iterable) else r_headers.keys()):
                self.assertIsNotNone(response.headers.get(k), response.headers)
                if isinstance(r_headers, Mapping):
                    self.assertEqual(r_headers[k], response.headers.get(k), response.headers)

        if r_none:
            self.assertEqual("", response.text)

        else:
            if r_is_json:
                try:
                    self.assertIsNotNone(response.json())
                except ValueError:
                    self.fail(("No JSON content detected", response.headers, response.text))

            r_schema_ignored_fields = r_schema_ignored_fields or []
            if r_schema and isinstance(r_schema, pydantic.BaseModel):
                r_model = type(r_schema)(**response.json())
                for key in r_schema_ignored_fields:
                    delattr(r_model, key)
                    delattr(r_schema, key)
                self.assertEqual(r_schema, r_model, response.json())
            elif r_schema and isinstance(r_schema, type) and issubclass(r_schema, pydantic.BaseModel):
                self.assertTrue(r_schema(**response.json()), response.json())

        if recent_callbacks is not None:
            while recent_callbacks:
                obj = self.callback_request_list.get(timeout=callback_timeout)
                if obj in recent_callbacks:
                    recent_callbacks.remove(obj)
                else:
                    self.fail(f"Unexpected callback {obj!r} is not in {recent_callbacks}")

        return response

    def login(self):
        response = requests.post(
            self.server + self.api_version_format.format(self.latest_api_version)[1:] + "/login",
            headers={"Content-Type": "application/x-www-form-urlencoded"},
            data="&".join([
                "grant_type=password",
                "client_id=",
                "client_secret=",
                "scope=password",
                f"username={urllib.parse.quote(self.auth[0])}",
                f"password={urllib.parse.quote(self.auth[1])}"
            ])
        )
        if response.ok:
            self.token = response.json()["access_token"]
        else:
            self.fail(f"Failed to login ({response.status_code})")

    def _start_api_server(self):
        def _mk_args(port, conf_path) -> list:
            return [
                sys.executable, "-m", "matebot_core", "run", "--port", str(port),
                "--config", conf_path, "--host", "127.0.0.1", "--workers", "1", "--no-access-log"
            ]

        config = _schemas.config.CoreConfig(**_settings.get_default_config())
        if conf.SERVER_LOGGING_OVERWRITE:
            config.logging = conf.SERVER_LOGGING_OVERWRITE
        config.database.debug_sql = conf.SQLALCHEMY_ECHOING
        config.database.connection = self.database_url
        config.server.password_iterations = 1
        with open(self.config_file, "w") as f:
            f.write(config.json())

        self.auth = ("application", secrets.token_urlsafe(16))
        config = _settings.config.CoreConfig(**_settings.read_settings_from_json_source(False))
        database.PRINT_SQLITE_WARNING = False
        database.init(config.database.connection, config.database.debug_sql)
        session = database.get_new_session()
        salt = secrets.token_urlsafe(16)
        session.add(models.Application(name=self.auth[0], password=auth.hash_password(self.auth[1], salt), salt=salt))
        session.commit()
        session.flush()
        session.close()

        self.server_port = random.randint(10000, 20000)

        for i in range(conf.MAX_SERVER_START_RETRIES):
            self.server_process = subprocess.Popen(
                _mk_args(self.server_port, self.config_file),
                stderr=subprocess.PIPE,
                stdout=subprocess.PIPE,
                start_new_session=True
            )

            for j in range(conf.MAX_SERVER_WAIT_RETRIES):
                try:
                    self.server_process.wait(conf.API_SUBPROCESS_START_WAIT_TIMEOUT)
                except subprocess.TimeoutExpired:
                    pass
                else:
                    self._quit_api_server()
                    self.server_port += 1
                    break

                try:
                    requests.get(self.server)
                    return
                except requests.exceptions.ConnectionError:
                    pass

            else:
                if self.server_process.poll() is not None:
                    self._quit_api_server()
                    self.server_port += 1

        else:
            self.server_process.terminate()
            outs, errs = self.server_process.communicate()
            return_code = self.server_process.poll()
            self._quit_api_server()
            self.fail(
                f"Failed to successfully start the API server after {conf.MAX_SERVER_WAIT_RETRIES} "
                f"tries. Server process returned code {return_code}.\n"
                f"{' STDERR '.center(80, '=')}\n{errs.decode('UTF-8')}\n"
                f"{' STDOUT '.center(80, '=')}\n{outs.decode('UTF-8')}"
            )

    def _run_callback_server(self):
        self.CallbackHandler.request_list = self.callback_request_list
        self.callback_server_port = random.randint(20000, 30000)

        for i in range(conf.MAX_SERVER_START_RETRIES):
            try:
                self.callback_server = http.server.HTTPServer(
                    ("127.0.0.1", self.callback_server_port),
                    self.CallbackHandler
                )
                self.callback_server.serve_forever()
                break
            except OSError as exc:
                if exc.errno != errno.EADDRINUSE:
                    raise
                self.callback_server_port += 1
        else:
            self.fail(f"Is the callback server port {self.callback_server_port} already occupied?")

    def _quit_api_server(self):
        if self.server_process is None:
            return
        self.server_process.terminate()
        try:
            self.server_process.wait(conf.API_SUBPROCESS_TERMINATE_TIMEOUT)
        except subprocess.TimeoutExpired:
            pass
        self.server_process.kill()
        try:
            self.server_process.wait(conf.API_SUBPROCESS_KILL_TIMEOUT)
        except subprocess.TimeoutExpired:
            pass
        self.server_process.stdout.close()
        self.server_process.stderr.close()

    def get_db_session(self) -> sqlalchemy.orm.Session:
        opts = {"echo": conf.SQLALCHEMY_ECHOING}
        if self.database_url.startswith("sqlite:"):
            opts = {"connect_args": {"check_same_thread": False}}
        engine = sqlalchemy.create_engine(self.database_url, **opts)
        return sqlalchemy.orm.sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=engine
        )()

    def make_special_user(self, community_name: str = "Community"):
        session = self.get_db_session()
        specials = session.query(models.User).filter_by(special=True).all()
        if len(specials) > 1:
            self.fail("CRITICAL ERROR. Please drop a bug report.")
        if len(specials) == 0:
            session.add(models.User(
                active=True,
                special=True,
                external=False,
                permission=False,
                name=community_name
            ))
            session.commit()
        session.close()

    def setUp(self) -> None:
        super().setUp()
        self.server_port = random.randint(10000, 20000)

        self._start_api_server()

        self.callback_request_list = queue.Queue()
        self.callback_server_port = random.randint(20000, 30000)
        self.callback_server_thread = threading.Thread(target=self._run_callback_server, daemon=True)
        self.callback_server_thread.start()

        for i in range(conf.MAX_SERVER_WAIT_RETRIES):
            try:
                requests.head(self.callback_server_uri)
                break
            except requests.exceptions.ConnectionError:
                self.callback_server_thread.join(0.05)
        else:
            self.fail("Failed to successfully start the callback server")

    def tearDown(self) -> None:
        self.callback_server.shutdown()
        self.callback_server.socket.close()
        self._quit_api_server()
        super().tearDown()

    @classmethod
    def setUpClass(cls) -> None:
        super().setUpClass()
        p = subprocess.run(
            [sys.executable, "-m", "matebot_core", "run", "-h"],
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE,
            start_new_session=True
        )
        if p.returncode != 0:
            raise RuntimeError("Executing the 'matebot_core' module from the current Python interpreter failed!")
