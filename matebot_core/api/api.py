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
from .routers import all_routers
from .. import schemas, __version__
from ..persistence import database
from ..settings import Settings
from .. import __file__ as _package_init_path


DEFAULT_EXCEPTION_HANDLERS = {
    base.APIException: base.APIException.handle,
    RequestValidationError: base.APIException.handle,
    StarletteHTTPException: base.APIException.handle,
    Exception: base.APIException.handle
}

LICENSE_INFO = {
    "name": "GNU General Public License v3",
    "url": "https://www.gnu.org/licenses/gpl-3.0.html"
}


API_V1_DOC = """MateBot core REST API definition version 1

This API requires authentication using OAuth2. Logging in with username
and password (see `POST /login`) yields a token that should be included
in the `Authorization` header with the type `Bearer`. It's an all-or-nothing
API without restrictions on queries, provided the query is valid and the
HTTP authorization with the bearer token was successful as well.

The API tries to always return JSON-encoded data to any kind of request,
if return data is necessary for that response, which is not the case for
redirects, for example. The only exception is `500` (Internal Server Error),
where no assumptions of the returned values can be made, even though even
those responses _should_ use the schema of the `APIError`, which is used
by all error responses issued by this API. This allows user agents to make
certain assumptions about the returned response, if the returned status
code equals the expected status code for that operation, usually `200` (OK).
Note that the `422` (Unprocessable Entity) error response means a problem in
the implementation in the user agent -- clients should never see any data
of the Unprocessable Entity responses, since the `details` field may
contain arbitrary data which is usually not user-friendly.

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
        responses=responses or {422: {"model": schemas.APIError}},
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

    if settings is None:
        settings = Settings()

    if configure_logging:
        logging.config.dictConfig(settings.logging.dict())
    logger = logging.getLogger(__name__)
    logger.debug("Starting application...")

    if configure_database:
        database.init(settings.database.connection, settings.database.echo)

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
                version="1.0",
                description=API_V1_DOC,
                static_directory=static_directory
            )
        },
        logger=logger,
        license_info=LICENSE_INFO,
        static_directory=static_directory,
        responses={422: {"model": schemas.APIError}},
        on_shutdown=[lambda: logger.info("Shutting down...")],
        api_class=versioning.VersionedFastAPI
    )

    assert isinstance(app, versioning.VersionedFastAPI), "'VersionedFastAPI' instance required"
    for router in all_routers:
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
