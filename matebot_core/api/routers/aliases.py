"""
MateBot router module for /aliases requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import APIRouter, Depends

from ..base import Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/aliases", tags=["Aliases"])


@router.get(
    "",
    response_model=List[schemas.Alias]
)
@versioning.versions(minimal=1)
async def search_for_aliases(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        user_id: Optional[pydantic.NonNegativeInt] = None,
        application_id: Optional[pydantic.NonNegativeInt] = None,
        app_username: Optional[pydantic.constr(max_length=255)] = None,
        confirmed: Optional[bool] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all aliases that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.Transaction,
        local,
        id=id,
        user_id=user_id,
        application_id=application_id,
        app_username=app_username,
        confirmed=confirmed
    )


@router.post(
    "",
    status_code=201,
    response_model=schemas.Alias,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def create_new_alias(
        alias: schemas.AliasCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new alias if no combination of `app_username` and `application_id` exists.

    The `app_username` field should reflect the internal username in the
    frontend application and may be any string with a maximum length of 255 chars.

    A 404 error will be returned if the `user_id` or `application_id` is not known.
    """

    user = await helpers.return_one(alias.user_id, models.User, local.session)
    application = await helpers.return_one(alias.application_id, models.Application, local.session)

    if not user.active:
        raise Conflict("A disabled user can't get new aliases.", str(alias))

    existing_alias = local.session.query(models.Alias).filter_by(
        application_id=application.id,
        app_username=alias.app_username
    ).first()
    if existing_alias is not None:
        raise Conflict(
            f"User alias {alias.app_username!r} can't be created since it already exists.",
            f"Alias: {existing_alias!r}"
        )

    model = models.Alias(
        user_id=user.id,
        application_id=application.id,
        app_username=alias.app_username,
        confirmed=alias.confirmed
    )
    return await helpers.create_new_of_model(model, local, logger)


@router.put(
    "",
    response_model=schemas.Alias,
    responses={k: {"model": schemas.APIError} for k in (404, 409)}
)
@versioning.versions(minimal=1)
async def update_existing_alias(
        alias: schemas.Alias,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing alias model identified by the `alias_id`.

    A 409 error will be returned if any other attribute than `app_username` or
    `confirmed` has been changed. A 404 error will be returned if at least one
    of the `alias_id`, `application_id` or `user_id` doesn't exist.
    """

    model = await helpers.return_one(alias.id, models.Alias, local.session)
    helpers.restrict_updates(alias, model.schema)
    await helpers.return_one(alias.user_id, models.User, local.session)
    await helpers.return_one(alias.application_id, models.Application, local.session)

    model.app_user_id = alias.app_username
    model.confirmed = alias.confirmed
    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)


@router.delete(
    "",
    status_code=204,
    responses={k: {"model": schemas.APIError} for k in (404, 409)}
)
@versioning.versions(minimal=1)
async def delete_existing_alias(
        alias: schemas.Alias,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing alias model.

    A 404 error will be returned if the requested `id` doesn't exist.
    A 409 error will be returned if the object is not up-to-date, which
    means that the user agent needs to get the object before proceeding.
    """

    return await helpers.delete_one_of_model(
        alias.id,
        models.Alias,
        local,
        schema=alias,
        logger=logger
    )
