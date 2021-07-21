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

from typing import List

import pydantic
from fastapi import FastAPI, Request, HTTPException, Depends
from fastapi.exceptions import RequestValidationError
from fastapi.responses import PlainTextResponse

from . import base, etag
from .base import _return_not_implemented_response
from .dependency import LocalRequestData
from .routers import aliases, communisms, refunds
from .. import schemas
from ..persistence import models


app = FastAPI(
    title="MateBot core REST API",
    version="0.3",
    description=__doc__
)

app.add_exception_handler(base.NotModified, etag.handle_cache_hit)
app.add_exception_handler(base.PreconditionFailed, etag.handle_failed_precondition)
app.add_exception_handler(base.MissingImplementation, base.MissingImplementation.handle)

app.include_router(aliases.router)
app.include_router(communisms.router)
app.include_router(refunds.router)



class Users:
    """
    TODO
    """

    @staticmethod
    @app.get(
        "/users",
        response_model=List[schemas.User],
        tags=["Users"],
        description="Return a list of all internal user models with their aliases."
    )
    def get_all_users():
        _return_not_implemented_response("get_all_users")

    @staticmethod
    @app.get(
        "/users/{user_id}",
        response_model=schemas.User,
        tags=["Users"],
        description="Return the internal model of the user specified by its user ID."
    )
    def get_user_by_id(user_id: int):
        _return_not_implemented_response("get_user_by_id")

    @staticmethod
    @app.post(
        "/users",
        response_model=schemas.User,
        tags=["Users"],
        description="Create a new \"empty\" user account with zero balance."
    )
    def create_new_user(user: schemas.IncomingUser):
        _return_not_implemented_response("create_new_user")

    @staticmethod
    @app.put(
        "/users",
        response_model=schemas.User,
        responses={404: {}, 409: {}},
        tags=["Users"],
        description="Update an existing user model identified by the `user_id`. A 404 error "
                    "will be returned if the `user_id` is not known. A 409 error will be "
                    "returned when some of the following fields have been changed compared "
                    "to the internal user state: `balance`, `created`, `accessed`."
    )
    def update_existing_user(user: schemas.User):
        _return_not_implemented_response("update_existing_user")


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
        _return_not_implemented_response("get_new_updates")


class Applications:
    """
    TODO
    """

    @staticmethod
    @app.get(
        "/applications",
        response_model=List[schemas.Application],
        tags=["Applications"],
        description="Return a list of all known applications with their respective ID (=`app_id`)."
    )
    def get_all_applications():
        _return_not_implemented_response("get_all_applications")

    @staticmethod
    @app.post(
        "/applications",
        response_model=schemas.Application,
        responses={409: {}},
        tags=["Applications"],
        description="Add a new application and create a new ID for it. The UUID `auth_token` "
                    "is used as a special form of API key to enforce proper authentication. "
                    "The required alias for the `special_user` is used to create a proper "
                    "binding to the \"banking user\" for the newly created application. "
                    "A 409 error will be returned if the application already exists."
    )
    def add_new_application(application: schemas.IncomingApplication):
        _return_not_implemented_response("add_new_application")


class Transactions:
    """
    TODO
    """

    @staticmethod
    @app.get(
        "/transactions",
        response_model=List[pydantic.NonNegativeInt],
        tags=["Transactions"],
        description="Return a list of all known transaction IDs in the system."
    )
    def get_all_known_transaction_ids():
        _return_not_implemented_response("get_all_known_transaction_ids")

    @staticmethod
    @app.get(
        "/transactions/{transaction_id}",
        response_model=schemas.Transaction,
        responses={404: {}},
        tags=["Transactions"],
        description="Return details about a specific transaction identified by its "
                    "`transaction_id`. A 404 error will be returned if that ID is unknown."
    )
    def get_transaction_by_id():
        _return_not_implemented_response("get_transaction_by_id")

    @staticmethod
    @app.get(
        "/transactions/user/{user_id}",
        response_model=List[schemas.Transaction],
        responses={404: {}},
        tags=["Transactions"],
        description="Return a list of all transactions made by a specific user identified by "
                    "its `user_id`. A 404 error will be returned if the user ID is unknown."
    )
    def get_all_transactions_of_user(user_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_all_transactions_of_user")

    @staticmethod
    @app.get(
        "/transactions/collective/{collective_id}",
        response_model=List[schemas.Transaction],
        responses={404: {}},
        tags=["Transactions"],
        description="Return a list of all transactions associated with a specific collective "
                    "operation identified by the `collective_id`. The list may be empty if "
                    "the collective operation was cancelled or not submitted yet. "
                    "A 404 error will be returned if the collective ID is unknown."
    )
    def get_all_transactions_of_collective(collective_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_all_transactions_of_collective")

    @staticmethod
    @app.post(
        "/transactions",
        response_model=schemas.Transaction,
        tags=["Transactions"],
        description="Make a new transaction using the specified data. Note that transactions "
                    "can't be edited after being sent to this endpoint by design, so take care. "
                    "The frontend application might want to introduce explicit user approval."
    )
    def make_a_new_transaction(transaction: schemas.IncomingTransaction):
        _return_not_implemented_response("make_a_new_transaction")
