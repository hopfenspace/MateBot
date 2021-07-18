"""
MateBot core REST API definitions
"""

from typing import List

import pydantic
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import schemas


app = FastAPI()


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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_users"
        })

    @staticmethod
    @app.get(
        "/users/{user_id}",
        response_model=schemas.User,
        tags=["Users"],
        description="Return the internal model of the user specified by its user ID."
    )
    def get_user_by_id(user_id: int):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_user_by_id"
        })


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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_new_updates"
        })


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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_known_aliases"
        })

    @staticmethod
    @app.get(
        "/aliases/application/{application}",
        response_model=List[schemas.UserAlias],
        tags=["Aliases"],
        description="Return a list of all users' aliases for a given application name."
    )
    def get_aliases_by_application_name(application: pydantic.constr(max_length=255)):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_alias_by_application_name"
        })

    @staticmethod
    @app.get(
        "/aliases/user/{user_id}",
        response_model=List[schemas.UserAlias],
        tags=["Aliases"],
        description="Return a list of all aliases of a user for a given user ID."
    )
    def get_aliases_by_user_id(user_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_aliases_by_user_id"
        })

    @staticmethod
    @app.get(
        "/aliases/id/{alias_id}",
        response_model=schemas.UserAlias,
        tags=["Aliases"],
        description="Return the alias model of a specific alias ID."
    )
    def get_alias_by_alias_id(alias_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_alias_by_alias_id"
        })

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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "create_new_alias"
        })

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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "update_existing_alias"
        })

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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "delete_existing_alias"
        })


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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_applications"
        })

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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "add_new_application"
        })


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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_known_transaction_ids"
        })

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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_transaction_by_id"
        })

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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_transactions_of_user"
        })

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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_transactions_of_collective"
        })

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
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "make_a_new_transaction"
        })


class Collectives:
    """
    TODO
    """

    @staticmethod
    @app.get(
        "/collectives",
        response_model=List[pydantic.NonNegativeInt],
        tags=["Collectives"],
        description="Return a list of all known collective IDs in the system."
    )
    def get_all_known_collective_ids():
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_known_collective_ids"
        })

    @staticmethod
    @app.get(
        "/collectives/{collective_id}",
        response_model=schemas.Collective,
        responses={404: {}},
        tags=["Collectives"],
        description="Return an existing collective. A 404 error will be returned "
                    "if the specified collective ID was not found."
    )
    def get_collective_by_id(collective_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_collective_by_id"
        })

    @staticmethod
    @app.get(
        "/collectives/creator/{user_id}",
        response_model=List[schemas.Collective],
        responses={404: {}},
        tags=["Collectives"],
        description="Return a list of all collectives which have been created by the user with "
                    "that `user_id`. A 404 error will be returned if the user ID is unknown."
    )
    def get_collectives_by_creator(user_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_collectives_by_creator"
        })

    @staticmethod
    @app.get(
        "/collectives/participant/{user_id}",
        response_model=List[schemas.Collective],
        responses={404: {}},
        tags=["Collectives"],
        description="Return a list of all collectives where the user with that `user_id` has "
                    "participated in. A 404 error will be returned if the user ID is unknown."
    )
    def get_collectives_by_participant(user_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_collectives_by_participant"
        })

    @staticmethod
    @app.post(
        "/collectives",
        response_model=schemas.Collective,
        responses={404: {}},
        tags=["Collectives"],
        description="Create a new collective based on the specified data. A 404 error will be "
                    "returned if the user ID of the creator of that collective is unknown."
    )
    def create_new_collective(collective: schemas.IncomingCollective):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "create_new_collective"
        })

    @staticmethod
    @app.put(
        "/collectives",
        response_model=schemas.Collective,
        responses={404: {}, 409: {}},
        tags=["Collectives"],
        description="Update an existing collective based on the specified data. A 404 error "
                    "will be returned if the collective ID was not found. A 409 error will "
                    "be returned if any of the following fields was changed (compared to the "
                    "previous values of that collective ID): `amount`, `description`, `creator`, "
                    "`active`, `communistic`. This prevents modifications of collective "
                    "operations after creation. Use the other POST methods if possible instead. "
                    "A 409 error will also be returned if a closed collective was altered."
    )
    def update_existing_collective(collective: schemas.Collective):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "update_existing_collective"
        })

    @staticmethod
    @app.post(
        "/collectives/{collective_id}/accept",
        response_model=schemas.SuccessfulCollective,
        responses={404: {}, 409: {}},
        tags=["Collectives"],
        description="Accept an existing collective operation. A 409 error will be returned if "
                    "this is attempted on a closed/inactive collective operation. A 404 error "
                    "will be returned if the specified `collective_id` is not known. This "
                    "operation closes the collective and prevents any further changes. Note "
                    "that this operation will implicitly also perform all transactions to "
                    "and from all members of the collective, so take care. A frontend "
                    "application might want to request explicit user approval before."
    )
    def accept_existing_collective(collective_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "accept_existing_collective"
        })

    @staticmethod
    @app.post(
        "/collectives/{collective_id}/cancel",
        response_model=schemas.Collective,
        responses={404: {}, 409: {}},
        tags=["Collectives"],
        description="Cancel an existing collective operation. A 409 error will be returned if "
                    "this is attempted on a closed/inactive collective operation. A 404 error "
                    "will be returned if the specified `collective_id` is not known. This "
                    "operation closes the collective and prevents any further changes. "
                    "No transactions will be performed based on this collective anymore."
    )
    def cancel_existing_collective(collective_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "cancel_existing_collective"
        })
