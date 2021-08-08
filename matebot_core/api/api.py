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

import logging.config

import fastapi.applications
from fastapi.staticfiles import StaticFiles
from fastapi.exceptions import RequestValidationError, StarletteHTTPException

try:
    import aiofiles
    static_docs = True
except ImportError:
    static_docs = False

from . import base
from .routers import all_routers
from .. import schemas, __api_version__
from ..persistence import database
from ..settings import Settings


settings = Settings()
logging.config.dictConfig(settings.logging.dict())
logging.getLogger(__name__).debug("Starting application...")
database.init(settings.database.connection, settings.database.echo)

app = fastapi.FastAPI(
    title="MateBot core REST API",
    version=__api_version__,
    docs_url=None,
    redoc_url=None,
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


if static_docs:
    app.mount("/static", StaticFiles(directory="static"), name="static")

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
