"""
MateBot router module for /aliases requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import Depends

from ._router import router
from ..base import BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...misc.notifier import Callback
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
    local.session.add(model)
    local.session.commit()

    Callback.push(
        schemas.EventType.ALIAS_CONFIRMED if alias.confirmed else schemas.EventType.ALIAS_CONFIRMATION_REQUESTED,
        {"id": model.id, "user": model.user_id, "app": model.application.name}
    )
    return model.schema


@router.post(
    "/aliases/confirm",
    tags=["Aliases"],
    response_model=schemas.Alias,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(minimal=1)
async def confirm_existing_alias(
        alias: schemas.IssuerIdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Confirm an existing unconfirmed alias model identified by the `alias_id`.
    If the alias is already confirmed, this endpoint will silently accept it.

    * `400`: if the issuer is not the alias owner
    * `404`: if the alias ID or the issuer user is unknown
    * `409`: if the target user is disabled or the community user
    """

    model = await helpers.return_one(alias.id, models.Alias, local.session)
    user = await helpers.resolve_user_spec(alias.issuer, local)
    if user.id != model.user_id:
        raise BadRequest("You are not permitted to confirm this alias, only the owner may do it.", str(model))
    if not user.active:
        raise Conflict("A disabled user can't handle aliases.", str(user))
    if user.special:
        raise Conflict("The community user can't handle aliases.")

    model.confirmed = True
    local.session.add(model)
    local.session.commit()

    Callback.push(
        schemas.EventType.ALIAS_CONFIRMED,
        {"id": model.id, "user": model.user_id, "app": model.application.name}
    )
    return model.schema


@router.post(
    "/aliases/delete",
    tags=["Aliases"],
    response_model=schemas.AliasDeletion,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(minimal=1)
async def delete_existing_alias(
        body: schemas.IssuerIdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing alias model.

    * `400`: if the issuer is not the alias owner
    * `404`: if the alias ID or the issuer user is unknown
    """

    model = await helpers.return_one(body.id, models.Alias, local.session)
    user = await helpers.resolve_user_spec(body.issuer, local)
    if user.id != model.user_id:
        raise BadRequest("You are not permitted to delete this alias, only the owner may do it.", str(user))
    return await helpers.delete_one_of_model(body.id, models.Alias, local, logger=logger)
