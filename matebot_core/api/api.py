"""
MateBot core REST API definitions

This API provides no multi-level security model with different privileges.
It's an all-or-nothing API, so take care when deploying it. It's
recommended to put a reverse proxy in front of this API to prevent
various problems and to introduce proper authentication or user handling.

Any client that wants to perform update operations using `PUT` should
be aware of the API's use of the `ETag` header. Any resource delivered
or created by a request will carry the `ETag` header set properly. This
allows the API to effectively prevent race conditions when multiple clients
want to update the same resource using `PUT`, since any such request will
only be performed if the `If-Match` header exists and is set correctly.
Take a look into the various `PUT` endpoints for more information.
"""

from typing import List

import pydantic
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import schemas


app = FastAPI(
    title="MateBot core REST API",
    version="0.3",
    description=__doc__
)


def _return_not_implemented_response(feature: str):
    return JSONResponse(status_code=501, content={
        "message": "Feature not implemented.",
        "feature": feature
    })


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
        responses={409: {}},
        tags=["Users"],
        description="Create a new \"empty\" user account. All aliases specified will "
                    "be attached to this user account, too. Trying to add a user alias "
                    "which is already occupied by another user will result in a 409 error."
    )
    def create_new_user(user: schemas.IncomingUser):
        _return_not_implemented_response("create_new_user")


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


class Aliases:
    """
    TODO
    """

    @staticmethod
    @app.get(
        "/aliases",
        response_model=List[schemas.UserAlias],
        tags=["Aliases"],
        description="Return a list of all known user aliases of all applications."
    )
    def get_all_known_aliases():
        _return_not_implemented_response("get_all_known_aliases")

    @staticmethod
    @app.get(
        "/aliases/application/{application}",
        response_model=List[schemas.UserAlias],
        tags=["Aliases"],
        description="Return a list of all users' aliases for a given application name."
    )
    def get_aliases_by_application_name(application: pydantic.constr(max_length=255)):
        _return_not_implemented_response("get_aliases_by_application_name")

    @staticmethod
    @app.get(
        "/aliases/user/{user_id}",
        response_model=List[schemas.UserAlias],
        tags=["Aliases"],
        description="Return a list of all aliases of a user for a given user ID."
    )
    def get_aliases_by_user_id(user_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_aliases_by_user_id")

    @staticmethod
    @app.get(
        "/aliases/id/{alias_id}",
        response_model=schemas.UserAlias,
        tags=["Aliases"],
        description="Return the alias model of a specific alias ID."
    )
    def get_alias_by_alias_id(alias_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_alias_by_alias_id")

    @staticmethod
    @app.post(
        "/aliases",
        status_code=201,
        response_model=schemas.UserAlias,
        responses={409: {}},
        tags=["Aliases"],
        description="Create a new alias, overwriting any existing alias of the same combination "
                    "of `app_user_id` and `application` ID. The `app_user_id` field should "
                    "reflect the unique internal username of the frontend application. A 409 "
                    "error will be returned when the combination of those already exists."
    )
    def create_new_alias(alias: schemas.IncomingUserAlias):
        _return_not_implemented_response("create_new_alias")

    @staticmethod
    @app.put(
        "/aliases",
        response_model=schemas.UserAlias,
        responses={404: {}, 409: {}},
        tags=["Aliases"],
        description="Update an existing alias model identified by the `alias_id`. Errors will "
                    "occur when the `alias_id` doesn't exist. It's also possible to overwrite "
                    "the previous unique `app_user_id` of that `alias_id`. A 409 error will be "
                    "returned when the combination of those already exists with another existing "
                    "`alias_id`, while a 404 error will be returned for an unknown `alias_id`."
    )
    def update_existing_alias(alias: schemas.UserAlias):
        _return_not_implemented_response("update_existing_alias")

    @staticmethod
    @app.delete(
        "/aliases/{alias_id}",
        status_code=204,
        responses={404: {}},
        tags=["Aliases"],
        description="Delete an existing alias model identified by the `alias_id`. "
                    "A 404 error will be returned for unknown `alias_id` values."
    )
    def delete_existing_alias(alias_id: int):
        _return_not_implemented_response("delete_existing_alias")


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


class Communisms:
    """
    TODO
    """

    @staticmethod
    @app.get(
        "/communisms",
        response_model=List[pydantic.NonNegativeInt],
        tags=["Communisms"],
        description="Return a list of all known communism IDs in the system."
    )
    def get_all_known_communism_ids():
        _return_not_implemented_response("get_all_known_communism_ids")

    @staticmethod
    @app.get(
        "/communisms/{communism_id}",
        response_model=schemas.Communism,
        responses={404: {}},
        tags=["Communisms"],
        description="Return an existing communism. A 404 error will be returned "
                    "if the specified communism ID was not found."
    )
    def get_communism_by_id(communism_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_communism_by_id")

    @staticmethod
    @app.get(
        "/communisms/creator/{user_id}",
        response_model=List[schemas.Communism],
        responses={404: {}},
        tags=["Communisms"],
        description="Return a list of all communisms which have been created by the user with "
                    "that `user_id`. A 404 error will be returned if the user ID is unknown."
    )
    def get_communisms_by_creator(user_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_communisms_by_creator")

    @staticmethod
    @app.get(
        "/communisms/participant/{user_id}",
        response_model=List[schemas.Communism],
        responses={404: {}},
        tags=["Communisms"],
        description="Return a list of all communisms where the user with that `user_id` has "
                    "participated in. A 404 error will be returned if the user ID is unknown."
    )
    def get_communisms_by_participant(user_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_communisms_by_participant")

    @staticmethod
    @app.post(
        "/communisms",
        response_model=schemas.Communism,
        responses={404: {}},
        tags=["Communisms"],
        description="Create a new communism based on the specified data. A 404 error will be "
                    "returned if the user ID of the creator of that communism is unknown."
    )
    def create_new_communism(communism: schemas.IncomingCommunism):
        _return_not_implemented_response("create_new_communism")

    @staticmethod
    @app.put(
        "/communisms",
        response_model=schemas.Communism,
        responses={404: {}, 409: {}},
        tags=["Communisms"],
        description="Update an existing communism based on the specified data. A 404 error "
                    "will be returned if the communism ID was not found. A 409 error will "
                    "be returned if any of the following fields was changed (compared to the "
                    "previous values of that communism ID): `amount`, `description`, `creator`, "
                    "`active`. This prevents modifications of communism operations after "
                    "creation. Use the other POST methods if possible instead. A 409 "
                    "error will also be returned if a closed communism was altered."
    )
    def update_existing_communism(communism: schemas.Communism):
        _return_not_implemented_response("update_existing_communism")

    @staticmethod
    @app.post(
        "/communisms/{communism_id}/accept",
        response_model=schemas.SuccessfulCommunism,
        responses={404: {}, 409: {}},
        tags=["Communisms"],
        description="Accept an existing communism operation. A 409 error will be returned if "
                    "this is attempted on a closed/inactive communism operation. A 404 error "
                    "will be returned if the specified `communism_id` is not known. This "
                    "operation closes the communism and prevents any further changes. Note "
                    "that this operation will implicitly also perform all transactions to "
                    "and from all members of the communism, so take care. A frontend "
                    "application might want to request explicit user approval before."
    )
    def accept_existing_communism(communism_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("accept_existing_communism")

    @staticmethod
    @app.post(
        "/communisms/{communism_id}/cancel",
        response_model=schemas.Communism,
        responses={404: {}, 409: {}},
        tags=["Communisms"],
        description="Cancel an existing communism operation. A 409 error will be returned if "
                    "this is attempted on a closed/inactive communism operation. A 404 error "
                    "will be returned if the specified `communism_id` is not known. This "
                    "operation closes the communism and prevents any further changes. "
                    "No transactions will be performed based on this communism anymore."
    )
    def cancel_existing_communism(communism_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("cancel_existing_communism")


class Refunds:
    """
    TODO
    """

    @staticmethod
    @app.get(
        "/refunds",
        response_model=List[pydantic.NonNegativeInt],
        tags=["Refunds"],
        description="Return a list of all known refund IDs in the system."
    )
    def get_all_known_refund_ids():
        _return_not_implemented_response("get_all_known_refund_ids")

    @staticmethod
    @app.get(
        "/refunds/{refund_id}",
        response_model=schemas.Refund,
        responses={404: {}},
        tags=["Refunds"],
        description="Return an existing refund. A 404 error will be returned "
                    "if the specified refund ID was not found."
    )
    def get_refund_by_id(refund_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_refund_by_id")

    @staticmethod
    @app.get(
        "/refunds/creator/{user_id}",
        response_model=List[schemas.Refund],
        responses={404: {}},
        tags=["Refunds"],
        description="Return a list of all refunds which have been created by the user with "
                    "that `user_id`. A 404 error will be returned if the user ID is unknown."
    )
    def get_refunds_by_creator(user_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("get_refunds_by_creator")

    @staticmethod
    @app.post(
        "/refunds",
        response_model=schemas.Refund,
        responses={404: {}},
        tags=["Refunds"],
        description="Create a new refund based on the specified data. A 404 error will be "
                    "returned if the user ID of the creator of that refund is unknown."
    )
    def create_new_refund(refund: schemas.IncomingRefund):
        _return_not_implemented_response("create_new_refund")

    @staticmethod
    @app.put(
        "/refunds",
        response_model=schemas.Refund,
        responses={404: {}, 409: {}},
        tags=["Refunds"],
        description="Update an existing refund based on the specified data. A 404 error "
                    "will be returned if the refund ID was not found. A 409 error will "
                    "be returned if any of the following fields was changed (compared to the "
                    "previous values of that refund ID): `amount`, `description`, `creator`, "
                    "`active`. This prevents modifications of refund requests after their "
                    "creation. A 409 error will also be returned if the operation was "
                    "performed on a closed refund. This method will merely update the votes "
                    "for approval or refusal of the refunding request. Use the other "
                    "POST method to eventually cancel a request if necessary."
    )
    def update_existing_refund(refund: schemas.Refund):
        _return_not_implemented_response("update_existing_refund")

    @staticmethod
    @app.post(
        "/refunds/{refund_id}/cancel",
        response_model=schemas.Refund,
        responses={404: {}, 409: {}},
        tags=["Refunds"],
        description="Cancel an existing refund operation. A 409 error will be returned if "
                    "this is attempted on a closed/inactive refund operation. A 404 error "
                    "will be returned if the specified `refund_id` is not known. This "
                    "operation closes the refund and prevents any further changes. "
                    "No transactions will be performed based on this refund anymore."
    )
    def cancel_existing_refund(refund_id: pydantic.NonNegativeInt):
        _return_not_implemented_response("cancel_existing_refund")
