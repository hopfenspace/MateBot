"""
MateBot core REST API definitions
"""

from typing import List

import pydantic
from fastapi import FastAPI
from fastapi.responses import JSONResponse

from . import schemas


app = FastAPI()

base_responses = {}


class Users:
    """
    TODO
    """

    @staticmethod
    @app.get("/users", response_model=List[schemas.User], responses=base_responses, tags=["Users"])
    def get_all_users():
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_users"
        })

    @staticmethod
    @app.get("/users/{user_id}", response_model=schemas.User, responses=base_responses, tags=["Users"])
    def get_user_by_id(user_id: int):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_user_by_id"
        })


class Aliases:
    """
    TODO
    """

    @staticmethod
    @app.get("/aliases/application/{application}", response_model=List[schemas.UserAlias], responses=base_responses, tags=["Aliases"])
    def get_aliases_by_application_name(application: pydantic.constr(max_length=255)):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_alias_by_application_name"
        })

    @staticmethod
    @app.get("/aliases/user/{user_id}", response_model=schemas.UserAlias, responses=base_responses, tags=["Aliases"])
    def get_aliases_by_user_id(user_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_aliases_by_user_id"
        })

    @staticmethod
    @app.get("/aliases/id/{alias_id}", response_model=schemas.UserAlias, responses=base_responses, tags=["Aliases"])
    def get_alias_by_alias_id(alias_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_alias_by_alias_id"
        })

    @staticmethod
    @app.post("/aliases", response_model=schemas.UserAlias, responses=base_responses, tags=["Aliases"])
    def create_new_alias(alias: schemas.IncomingUserAlias):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "create_new_alias"
        })

    @staticmethod
    @app.put("/aliases", response_model=schemas.UserAlias, responses=base_responses, tags=["Aliases"])
    def update_existing_alias(alias: schemas.UserAlias):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "update_existing_alias"
        })

    @staticmethod
    @app.delete("/aliases", status_code=204, responses={204: {"description": "Successful Delete"}}, tags=["Aliases"])
    def delete_existing_alias(alias: schemas.UserAlias):
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
    @app.get("/applications", response_model=List[schemas.Application], responses=base_responses, tags=["Applications"])
    def get_all_applications():
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_all_applications"
        })

    @staticmethod
    @app.get("/applications/name/{name}", response_model=schemas.Application, responses=base_responses, tags=["Applications"])
    def get_application_by_name(name: pydantic.constr(max_length=255)):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_application_by_name"
        })

    @staticmethod
    @app.get("/applications/id/{app_id}", response_model=schemas.Application, responses=base_responses, tags=["Applications"])
    def get_application_by_id(app_id: pydantic.NonNegativeInt):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "get_application_by_name"
        })

    @staticmethod
    @app.post("/applications", response_model=schemas.Application, responses=base_responses, tags=["Applications"])
    def add_new_application(application: schemas.IncomingApplication):
        # TODO
        return JSONResponse(status_code=501, content={
            "message": "Feature not implemented.",
            "feature": "add_new_application"
        })
