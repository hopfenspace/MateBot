"""
MateBot router module for /aliases requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import Depends

from ._router import router
from ..base import Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)


@router.get("/aliases", tags=["Aliases"], response_model=List[schemas.Alias])
@versioning.versions(minimal=1)
async def search_for_aliases(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        user_id: Optional[pydantic.NonNegativeInt] = None,
        application_id: Optional[pydantic.NonNegativeInt] = None,
        username: Optional[pydantic.constr(max_length=255)] = None,
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
        username=username,
        confirmed=confirmed
    )


@router.post(
    "/aliases",
    tags=["Aliases"],
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
    Create a new alias if no combination of `username` and `application_id` exists

    The `username` field should reflect the internal username in the
    frontend application and may be any string with a maximum length of 255 chars.

    * `404`: if the user ID or application ID is unknown
    * `409`: if the referenced user is disabled
    """

    user = await helpers.return_one(alias.user_id, models.User, local.session)
    application = await helpers.return_one(alias.application_id, models.Application, local.session)

    if not user.active:
        raise Conflict("A disabled user can't get new aliases.", str(alias))

    existing_alias = local.session.query(models.Alias).filter_by(
        application_id=application.id,
        username=alias.username
    ).first()
    if existing_alias is not None:
        raise Conflict(
            f"User alias {alias.username!r} can't be created since it already exists.",
            str(existing_alias)
        )

    model = models.Alias(
        user_id=user.id,
        application_id=application.id,
        username=alias.username,
        confirmed=alias.confirmed
    )
    return await helpers.create_new_of_model(model, local, logger)


@router.put(
    "/aliases",
    tags=["Aliases"],
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

    * `404`: if the alias ID, user ID or application ID is unknown
    * `409`: if the target user is disabled or the alias combination already exists
    """

    model = await helpers.return_one(alias.id, models.Alias, local.session)
    user = await helpers.return_one(alias.user_id, models.User, local.session)
    if not user.active:
        raise Conflict("A disabled user can't get new aliases.", str(alias))
    await helpers.return_one(alias.application_id, models.Application, local.session)

    existing_alias = local.session.query(models.Alias).filter_by(
        application_id=alias.application_id,
        username=alias.username
    ).first()
    if existing_alias is not None:
        raise Conflict(
            f"User alias {alias.username!r} can't be created since it already exists.",
            str(existing_alias)
        )

    model.user_id = user.id
    model.application_id = alias.application_id
    model.username = alias.username
    model.confirmed = alias.confirmed
    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)


@router.delete(
    "/aliases",
    tags=["Aliases"],
    status_code=204,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def delete_existing_alias(
        alias: schemas.Alias,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing alias model.

    * `404`: if the requested alias ID doesn't exist
    """

    return await helpers.delete_one_of_model(alias.id, models.Alias, local, logger=logger)
