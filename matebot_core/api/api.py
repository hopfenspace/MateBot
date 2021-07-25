"""
MateBot core REST API definitions

This API provides no multi-level security model with different privileges.
It's an all-or-nothing API, so take care when deploying it. It's
recommended to put a reverse proxy in front of this API to prevent
various problems and to introduce proper authentication or user handling.

The API tries to always return JSON-encoded data to any kind of request,
if return data is necessary for that response, which is not the case for
redirects, for example. The only exception is 500 (Internal Server Error),
where no assumptions of the returned values can be made. Most of the errors
returned by the API use the `APIError` model to represent their data.
The only known exception at the moment are 404 (Not Found) and 405 (Method
Not Allowed), which are not considered as API problems, since the API is
properly documented for that. This allows user agents to make certain
assumptions about the returned response, if the returned status code
equals the expected status code for that operation, usually 200 (OK).

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

from fastapi import FastAPI
from fastapi.exceptions import RequestValidationError

from . import base
from .routers import aliases, applications, ballots, communisms, generic, refunds, transactions, users, votes
from .. import schemas


app = FastAPI(
    title="MateBot core REST API",
    version="0.3",
    description=__doc__,
    responses={422: {"model": schemas.APIError}}
)

app.add_exception_handler(base.NotModified, base.NotModified.handle)
app.add_exception_handler(base.PreconditionFailed, base.PreconditionFailed.handle)
app.add_exception_handler(base.MissingImplementation, base.MissingImplementation.handle)
app.add_exception_handler(RequestValidationError, base.APIException.handle)

app.include_router(generic.router)

app.include_router(aliases.router)
app.include_router(applications.router)
app.include_router(ballots.router)
app.include_router(communisms.router)
app.include_router(refunds.router)
app.include_router(transactions.router)
app.include_router(users.router)
app.include_router(votes.router)
