"""
Combined MateBot core REST API definitions

This API may provide multiple versions of certain endpoints.
Take a look into the different API definitions to see which
functionality they provide. Take a look into the changelogs
for more information about the breaking changes between versions.
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

from . import base, versioning
from .routers import all_routers
from .. import schemas, __version__
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

    if configure_database:
        database.init(settings.database.connection, settings.database.echo)

    app = versioning.VersionedFastAPI(
        title="MateBot core REST API",
        version=__version__,
        docs_url=None if static_docs and configure_static_docs else "/docs",
        redoc_url=None if static_docs and configure_static_docs else "/redoc",
        description=__doc__,
        responses={422: {"model": schemas.APIError}}
    )

    app.add_exception_handler(base.APIException, base.APIException.handle)
    app.add_exception_handler(RequestValidationError, base.APIException.handle)
    app.add_exception_handler(StarletteHTTPException, base.APIException.handle)
    app.add_exception_handler(Exception, base.APIException.handle)

    @app.get("/", include_in_schema=False)
    async def get_root():
        return fastapi.responses.RedirectResponse("/docs")

    static_dirs = [
        static_directory for static_directory in [
            os.path.join(os.path.abspath("."), "static"),
            os.path.join(os.path.split(os.path.abspath(_package_init_path))[0], "static")
        ]
        if os.path.exists(static_directory)
    ]
    if len(static_dirs) > 1:
        logger.warning("More than one static directory found! Though unexpected, it may be fine.")

    if static_docs and configure_static_docs and StaticFiles and len(static_dirs) > 0:
        app.mount("/static", StaticFiles(directory=static_dirs[0]), name="static")

        @app.get("/redoc", include_in_schema=False)
        async def get_redoc():
            return fastapi.applications.get_redoc_html(
                openapi_url=app.openapi_url,
                title=app.title + " - ReDoc",
                redoc_js_url="/static/redoc.standalone.js",
                redoc_favicon_url="/static/img/favicon.ico",
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
                swagger_favicon_url="/static/img/favicon.ico"
            )

        @app.get(app.swagger_ui_oauth2_redirect_url, include_in_schema=False)
        async def get_swagger_ui_redirect():
            return fastapi.applications.get_swagger_ui_oauth2_redirect_html()

    elif static_docs and configure_static_docs and StaticFiles:
        logger.warning("Configuring static files failed since some resources were not found.")
    elif configure_static_docs and not static_docs:
        logger.error("Configuring static files was not possible due to unmet dependencies!")

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
