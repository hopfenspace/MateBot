"""
MateBot router module for /aliases requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import MissingImplementation, APIException
from ..dependency import LocalRequestData
from .. import helpers
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/aliases",
    tags=["Aliases"]
)


@router.get(
    "",
    response_model=List[schemas.Alias],
    description="Return a list of all known user aliases of all applications."
)
def get_all_known_aliases(local: LocalRequestData = Depends(LocalRequestData)):
    return helpers.get_all_of_model(models.UserAlias, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Alias,
    responses={409: {}},
    description="Create a new alias, failing for any existing alias of the same combination "
                "of `app_user_id` and `application` ID. The `app_user_id` field should "
                "reflect the unique internal username in the frontend application. A 409 "
                "error will be returned when the combination of those already exists. A 404 "
                "error will be returned if the `user_id` or `application` is not known."
)
def create_new_alias(
        alias: schemas.AliasCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    user = local.session.get(models.User, alias.user_id)
    if user is None:
        raise APIException(
            status_code=404,
            detail="",
            repeat=False,
            message=f"User ID {alias.user_id!r} was not found."
        )

    application = local.session.query(models.Application).filter_by(name=alias.application).first()
    if application is None:
        raise APIException(
            status_code=404,
            detail="",
            repeat=False,
            message=f"Application {alias.application!r} was not found."
        )

    existing_alias = local.session.query(models.UserAlias).filter_by(
        app_id=application.id,
        app_user_id=alias.app_user_id
    ).first()
    if existing_alias is not None:
        raise APIException(
            status_code=409,
            detail=f"Alias: {existing_alias!r}",
            repeat=False,
            message=f"User alias can't be created since it already exists."
        )

    model = models.UserAlias(
        user_id=user.id,
        app_id=application.id,
        app_user_id=alias.app_user_id
    )
    return helpers.create_new_of_model(model, local, logger)


@router.put(
    "",
    response_model=schemas.Alias,
    responses={404: {}, 409: {}},
    description="Update an existing alias model identified by the `alias_id`. Errors will "
                "occur when the `alias_id` doesn't exist. It's also possible to overwrite "
                "the previous unique `app_user_id` of that `alias_id`. A 409 error will be "
                "returned when the combination of those already exists with another existing "
                "`alias_id`, while a 404 error will be returned for an unknown `alias_id`."
)
def update_existing_alias(
        alias: schemas.Alias,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("update_existing_alias")


@router.delete(
    "/{alias_id}",
    status_code=204,
    responses={404: {}},
    description="Delete an existing alias model identified by the `alias_id`. "
                "A 404 error will be returned for unknown `alias_id` values."
)
def delete_existing_alias(
        alias_id: int,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("delete_existing_alias")


@router.get(
    "/application/{application}",
    response_model=List[schemas.Alias],
    description="Return a list of all users' aliases for a given application name."
)
def get_aliases_by_application_name(
        application: pydantic.constr(max_length=255),
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_aliases_by_application_name")


@router.get(
    "/user/{user_id}",
    response_model=List[schemas.Alias],
    description="Return a list of all aliases of a user for a given user ID."
)
def get_aliases_by_user_id(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_aliases_by_user_id")


@router.get(
    "/id/{alias_id}",
    response_model=schemas.Alias,
    description="Return the alias model of a specific alias ID."
)
def get_alias_by_alias_id(
        alias_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_alias_by_alias_id")
