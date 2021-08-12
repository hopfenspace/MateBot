"""
MateBot core REST API definitions

This API provides no multi-level security model with different privileges.
It's an all-or-nothing API, so take care when deploying it. It's
recommended to put a reverse proxy in front of this API to prevent
various problems and to introduce proper authentication or user handling.

The API tries to always return JSON-encoded data to any kind of request,
if return data is necessary for that response, which is not the case for
redirects, for example. The only exception is 500 (Internal Server Error),
where no assumptions of the returned values can be made, even though even
those responses _should_ use the schema of the `APIError`, which is used
by all error responses issued by this API. This allows user agents to make
certain assumptions about the returned response, if the returned status
code equals the expected status code for that operation, usually 200 (OK).
Note that the Unprocessable Entity (422) error response means a problem in
the implementation in the user agent -- clients should never see any data
of the Unprocessable Entity responses, since the `details` field may
contain arbitrary data which is usually not user-friendly.

This API supports conditional HTTP requests and will enforce them for
various types of request that change a resource's state. Any resource
delivered or created by a request will carry the `ETag` header
set properly (exceptions are any kind of error response or those
tagged 'generic'). This allows the API to effectively prevent race
conditions when multiple clients want to update the same resource
using `PUT`. Take a look into RFC 7232 for more information. Note
that the `If-Match` header field is the only one used by this API.

The handling of incoming conditional requests is described as follows:

1. Calculate the current `ETag` of the local resource in question
2. In case the `If-Match` header field contains the special value `*` ...
    1. and the previous step returned no valid `ETag`, because the resource
       in question doesn't exist yet, respond with 412 (Precondition Failed)
    2. and the resource in question exists, perform the operation as usual
3. In case the `If-Match` header field contains that tag ...
    1. and the method is `GET`, respond with 304 (Not Modified)
    2. and for other methods, perform the operation as usual
4. Otherwise ...
    1. and the method is `GET` or `POST`, perform the operation as usual
    2. and for other methods, respond with 412 (Precondition Failed)
"""

import os
import logging.config
from typing import Optional

import fastapi.applications
from fastapi.exceptions import RequestValidationError, StarletteHTTPException

try:
    from fastapi.staticfiles import StaticFiles
    static_docs = True
except ImportError:
    StaticFiles = None
    static_docs = False

from . import base
from .routers import all_routers
from .. import schemas, __api_version__
from ..persistence import database
from ..settings import Settings
from .. import __file__ as _package_init_path


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

    def check_static_configuration() -> Optional[str]:
        """
        Check for the existence of all required static files and return the static dir on success
        """

        static_dir = os.path.join(os.path.split(os.path.abspath(_package_init_path))[0], "static")
        static_files = [
            "redoc.standalone.js",
            "swagger-ui.css",
            "swagger-ui-bundle.js"
        ]

        if os.path.exists(static_dir):
            for static_file in static_files:
                if not os.path.exists(os.path.join(static_dir, static_file)):
                    logger.error(f"File not found: {os.path.join(static_dir, static_file)!r}")
                    return None
            return static_dir
        else:
            logger.error(f"Static directory {static_dir!r} not found!")
        return None

    if configure_database:
        database.init(settings.database.connection, settings.database.echo)

    app = fastapi.FastAPI(
        title="MateBot core REST API",
        version=__api_version__,
        docs_url=None if static_docs and configure_static_docs else "/docs",
        redoc_url=None if static_docs and configure_static_docs else "/redoc",
        description=__doc__,
        responses={422: {"model": schemas.APIError}}
    )

    app.add_exception_handler(base.APIException, base.APIException.handle)
    app.add_exception_handler(RequestValidationError, base.APIException.handle)
    app.add_exception_handler(StarletteHTTPException, base.APIException.handle)
    app.add_exception_handler(Exception, base.APIException.handle)

    for router in all_routers:
        app.include_router(router)

    @app.get("/", include_in_schema=False)
    async def get_root():
        return fastapi.responses.RedirectResponse("/docs")

    if static_docs and configure_static_docs and StaticFiles and check_static_configuration():
        app.mount("/static", StaticFiles(directory=check_static_configuration()), name="static")

        @app.get("/redoc", include_in_schema=False)
        async def get_redoc():
            return fastapi.applications.get_redoc_html(
                openapi_url=app.openapi_url,
                title=app.title + " - ReDoc",
                redoc_js_url="/static/redoc.standalone.js",
                redoc_favicon_url="/static/favicon.png",
                with_google_fonts=False
            )

        @app.get("/docs", include_in_schema=False)
        async def get_swagger_ui():
            return fastapi.applications.get_swagger_ui_html(
                openapi_url=app.openapi_url,
                title=app.title + " - Swagger UI",
                oauth2_redirect_url=app.swagger_ui_oauth2_redirect_url,
                swagger_js_url="/static/swagger-ui-bundle.js",
                swagger_css_url="/static/swagger-ui.css",
                swagger_favicon_url="/static/favicon.png"
            )

        @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
        async def get_swagger_ui_redirect():
            return fastapi.applications.get_swagger_ui_oauth2_redirect_html()

    elif static_docs and configure_static_docs and StaticFiles:
        logger.warning("Configuring static files failed since some resources were not found.")

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
