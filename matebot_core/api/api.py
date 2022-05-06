"""
Combined MateBot core REST API definitions

This API may provide multiple versions of certain endpoints.
Take a look into the different API definitions to see which
functionality they provide. Take a look into the changelogs
for more information about the breaking changes between versions.
"""

import os
import logging.config
from typing import Any, Callable, Dict, Optional, Type, Union

import fastapi.applications
from fastapi.exceptions import RequestValidationError, StarletteHTTPException

try:
    from fastapi.staticfiles import StaticFiles
except ImportError:
    StaticFiles = None

from . import base, versioning
from .routers import router
from .. import schemas, __version__
from ..misc import notifier
from ..persistence import database
from ..settings import Settings
from .. import __file__ as _package_init_path


DEFAULT_EXCEPTION_HANDLERS = {
    StarletteHTTPException: base.APIException.handle,
    RequestValidationError: base.handle_request_validation_error,
    Exception: base.handle_generic_exception
}

LICENSE_INFO = {
    "name": "GNU General Public License v3",
    "url": "https://www.gnu.org/licenses/gpl-3.0.html"
}


API_V1_DOC = """MateBot core REST API definition version 1

This API requires authentication using JSON web tokens. Logging in with username
and password (see `POST /login`) yields a token that should be included
in the `Authorization` header with the type `Bearer`. It's an all-or-nothing
API without restrictions on queries, provided the request is valid and the
HTTP authorization with the bearer token was successful as well.

The API tries to always return JSON-encoded data to any kind of request,
if return data is necessary for that response, which is not the case for
redirects, for example. The only exception is `500` (Internal Server Error),
where no assumptions of the returned values can be made, even though even
those responses _should_ use the schema of the `APIError`, which is used
by all error responses issued by this API. This allows user agents to make
certain assumptions about the returned response, if the returned status
code equals the expected status code for that operation, usually `200` (OK).

The following documentation provides in-depth information about the available
endpoints, their calling convention and returned responses. In general, the
following four different `4xx` error responses are used in the API code:

1. The `400` (Bad Request) error response is usually adequate to show to end
   users. It contains few or none technical details in the `message` field,
   which can be used to answer end user requests properly. Note that the
   `400` (Bad Request) response will be used on invalid requests by the client,
   too. This means that a client should validate user data as far as possible
   before sending it to the API, if the error message should be customized.
2. The `401` (Unauthorized) error response is encountered whenever a request
   is not properly authorized and therefore rejected. Either the user didn't
   supply an API token, the API token has already expired or is otherwise
   invalid. If a client encounters such a response, it should use the
   `POST /login` endpoint with its username and password to gather a fresh API
   token, which should be included in the `Authorization` header field.
3. The `404` (Not Found) error response usually indicates inadequate pre-checks
   of user supplied input or commands or invalid state in the client app.
   Client applications should avoid having a state and should be implemented as
   lazy as possible, anyways. It's returned whenever a model ID can't be found.
4. The `409` (Conflict) error response is usually not adequate for end users,
   since it may contain technical information. It may be seen if certain logical
   or database constraints are violated. The user agent should usually try to
   debug the problems itself, since the error probably results from inadequate
   checks of user input or user commands. It may also be yielded if the user
   agent tries to perform an action that violates the business logic of the
   server, but which should never be accessible to an end user anyways. One
   such example is trying to send money from the community user without refund.

Take a look at the individual methods and endpoints for more information.
"""


def _make_app(
        title: str,
        version: str,
        description: str,
        license_info: Optional[Dict[str, str]] = None,
        static_directory: Optional[str] = None,
        exception_handlers: Optional[Dict[Exception, Callable]] = None,
        root_redirect: bool = True,
        responses: Optional[Dict[Union[int, str], Dict[str, Any]]] = None,
        api_class: Optional[Type[fastapi.FastAPI]] = None,
        **kwargs
) -> fastapi.FastAPI:
    if api_class is None:
        api_class = fastapi.FastAPI
    app = api_class(
        title=title,
        version=version,
        description=description,
        license_info=license_info or LICENSE_INFO,
        docs_url=None if static_directory else "/docs",
        redoc_url=None if static_directory else "/redoc",
        responses=responses or {400: {"model": schemas.APIError}},
        **kwargs
    )

    handlers = exception_handlers or DEFAULT_EXCEPTION_HANDLERS
    for exc in handlers:
        app.add_exception_handler(exc, handlers[exc])

    if root_redirect:
        @app.get("/", include_in_schema=False)
        async def redirect_root():
            return fastapi.responses.RedirectResponse("./docs")

    if static_directory:
        app.mount("/static", StaticFiles(directory=static_directory), name="static")

        @app.get("/redoc", include_in_schema=False)
        async def get_redoc(request: fastapi.Request):
            root_path = request.scope.get("root_path", "").rstrip("/")
            openapi_url = root_path + app.openapi_url
            return fastapi.applications.get_redoc_html(
                openapi_url=openapi_url,
                title=app.title + " - ReDoc",
                redoc_js_url="/static/redoc.standalone.js",
                redoc_favicon_url="/static/img/favicon.ico",
                with_google_fonts=False
            )

        @app.get("/docs", include_in_schema=False)
        async def get_swagger_ui(request: fastapi.Request):
            root_path = request.scope.get("root_path", "").rstrip("/")
            openapi_url = root_path + app.openapi_url
            oauth2_redirect_url = app.swagger_ui_oauth2_redirect_url
            if oauth2_redirect_url:
                oauth2_redirect_url = root_path + oauth2_redirect_url
            return fastapi.applications.get_swagger_ui_html(
                openapi_url=openapi_url,
                title=app.title + " - Swagger UI",
                oauth2_redirect_url=oauth2_redirect_url,
                swagger_js_url="/static/swagger-ui-bundle.js",
                swagger_css_url="/static/swagger-ui.css",
                swagger_favicon_url="/static/img/favicon.ico"
            )

        if app.swagger_ui_oauth2_redirect_url:
            @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
            async def get_swagger_ui_redirect():
                return fastapi.applications.get_swagger_ui_oauth2_redirect_html()

    return app


def create_app(
        settings: Optional[Settings] = None,
        configure_logging: bool = True,
        configure_database: bool = True,
        configure_static_docs: bool = True
) -> fastapi.FastAPI:
    """
    Create a new ``FastAPI`` instance using the specified settings and switches

    This function is conveniently used to allow overwriting the settings
    before launching the application as well as to allow multiple ``FastAPI``
    instances in one program, which in turn makes unit testing much easier.

    :param settings: optional Settings instance (would be created if not present)
    :param configure_logging: switch whether to configure logging
    :param configure_database: switch whether to configure the database
    :param configure_static_docs: switch whether to configure static assets for docs
    :return: new ``FastAPI`` instance
    """

    def startup_server():
        logger.info("Starting API...")
        logger.debug(f"Notifying callbacks of SERVER_STARTED event...")
        notifier.Callback.push(schemas.EventType.SERVER_STARTED, {"base_url": settings.server.public_base_url})

    def shutdown_server():
        logger.info("Shutting down...")
        notifier.Callback.shutdown_event.set()

    if settings is None:
        settings = Settings()

    if configure_logging:
        logging.config.dictConfig(settings.logging.dict())
    logger = logging.getLogger(__name__)
    logger.debug("Starting application...")

    if configure_database:
        database.init(settings.database.connection, settings.database.debug_sql)

    static_dirs = [
        static_directory for static_directory in [
            os.path.join(os.path.abspath("."), "static"),
            os.path.join(os.path.split(os.path.abspath(_package_init_path))[0], "static")
        ]
        if os.path.exists(static_directory)
    ]
    if len(static_dirs) > 1:
        logger.warning("More than one static directory found! Though unexpected, it may be fine.")

    static_directory = None
    if configure_static_docs and StaticFiles and len(static_dirs) == 0:
        logger.warning("Configuring static files failed since some resources were not found.")
    elif configure_static_docs and not StaticFiles:
        logger.error("Configuring static files was not possible due to unmet dependencies!")
    else:
        static_directory = static_dirs[0]

    app = _make_app(
        title="MateBot core REST API",
        version=__version__,
        description=__doc__,
        apis={
            1: _make_app(
                title="MateBot core REST API v1",
                version=__version__,
                description=API_V1_DOC,
                static_directory=static_directory,
                api_class=base.APIWithoutValidationError,
                responses={400: {"model": schemas.APIError}, 401: {"model": schemas.APIError}}
            )
        },
        logger=logger,
        license_info=LICENSE_INFO,
        static_directory=static_directory,
        responses={400: {"model": schemas.APIError}},
        on_startup=[startup_server],
        on_shutdown=[shutdown_server],
        api_class=versioning.VersionedFastAPI
    )

    assert isinstance(app, versioning.VersionedFastAPI), "'VersionedFastAPI' instance required"
    app.add_router(router)

    app.finish()
    return app


class APIWrapper:
    """
    Wrapper class around the FastAPI main object, accessible via the ``app`` property

    There should be only one global instance of this object, which should only
    export its functionality to hold the ``app`` property. This wrapper can be
    used to allow easy command-line usage via ``uvicorn`` calls. Example:

    .. code-block::

        uvicorn matebot_core.api:api.app
    """

    def __init__(self):
        self._app: Optional[fastapi.FastAPI] = None

    def get_app(self) -> fastapi.FastAPI:
        return self.app

    def set_app(self, application: fastapi.FastAPI):
        if not isinstance(application, fastapi.FastAPI):
            raise TypeError
        self._app = application

    @property
    def app(self) -> fastapi.FastAPI:
        """
        Return the ``app`` instance (or create it with default settings if it doesn't exist)
        """

        if self._app is not None:
            return self._app
        self._app = create_app()
        return self._app


api = APIWrapper()
