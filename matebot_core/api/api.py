"""
MateBot core REST API definitions

This API provides no multi-level security model with different privileges.
It's an all-or-nothing API, so take care when deploying it. It's
recommended to put a reverse proxy in front of this API to prevent
various problems and to introduce proper authentication or user handling.

This API supports conditional HTTP requests and will enforce them for
various types of request that change a resource's state. Any resource
delivered or created by a request will carry the `ETag` header
set properly. This allows the API to effectively prevent race
conditions when multiple clients want to update the same resource
using `PUT`. Take a look into RFCs 7232 for more information.
Note that the `Last-Modified` header field is not used by this API.

The handling of incoming conditional requests is described below:

1. Evaluate the `If-Match` precondition:
  * true and method is `GET`, respond with 304 (Not Modified)
  * true for other methods, continue with step 2 and set `verified` mark
  * false, respond with 412 (Precondition Failed)
  * header field absent, continue with step 2 without mark
2. Evaluate the `If-None-Match` precondition:
  * true, continue with step 3 and set `verified` mark
  * false and method is `GET`, respond with 304 (Not Modified)
  * false for other methods, respond 412 (Precondition Failed)
  * header field absent, continue with step 3 without mark
3. Perform the requested operation:
  * method is `GET`, return the requested resource
  * method is `POST`, create the requested resource and return it
  * for other methods without mark, respond 412 (Precondition Failed)
  * for other methods with `verified` mark, perform the operation
"""


import pydantic
from fastapi import FastAPI, Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse

from . import base, etag
from .routers import aliases, applications, communisms, refunds, transactions, users
from .. import schemas


app = FastAPI(
    title="MateBot core REST API",
    version="0.3",
    description=__doc__
)

app.add_exception_handler(base.NotModified, base.NotModified.handle)
app.add_exception_handler(base.PreconditionFailed, base.PreconditionFailed.handle)
app.add_exception_handler(base.MissingImplementation, base.MissingImplementation.handle)

app.include_router(aliases.router)
app.include_router(applications.router)
app.include_router(communisms.router)
app.include_router(refunds.router)
app.include_router(transactions.router)
app.include_router(users.router)


class Updates:
    """
    TODO
    """

    @staticmethod
    @app.get(
        "/updates/{timestamp}",
        response_model=schemas.Updates,
        tags=["Updates"],
        description="Return a collection of new or updated models since the specified UNIX "
                    "timestamp. This collection must not necessarily be complete."
    )
    def get_new_updates(timestamp: pydantic.NonNegativeInt):
        raise base.MissingImplementation("get_new_updates")
