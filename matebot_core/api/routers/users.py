"""
MateBot router module for /users requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/users",
    tags=["Users"]
)


@router.get(
    "",
    response_model=List[schemas.User]
)
@versioning.versions(minimal=1)
async def get_all_users(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all internal user models with their aliases.
    """

    return await helpers.get_all_of_model(models.User, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.User
)
@versioning.versions(minimal=1)
async def create_new_user(
        user: schemas.UserCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new "empty" user account with zero balance.
    """

    values = user.dict()
    values["voucher_id"] = values.pop("voucher")
    model = models.User(**values)
    return await helpers.create_new_of_model(model, local, logger, "/users/{}", True)


@router.put(
    "",
    response_model=schemas.User,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def update_existing_user(
        user: schemas.User,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing user model identified by the `user_id`.

    A 404 error will be returned if the `user_id` or `voucher` is not known.
    A 409 error will be returned when some of the following fields have been
    changed compared to the internal user state: `balance`, `created`, `accessed`.
    A 409 error will also be returned if the voucher ID equals the user ID.
    """

    model = await helpers.return_one(user.id, models.User, local.session)
    helpers.restrict_updates(user, model.schema)

    if model.id == user.voucher:
        raise Conflict("A user can't vouch for itself.", str(user))

    model.name = user.name
    model.permission = user.permission
    model.active = user.active
    model.external = user.external
    model.voucher_user = await helpers.return_one(user.voucher, models.User, local.session)

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)


@router.delete(
    "",
    status_code=204,
    responses={k: {"model": schemas.APIError} for k in (404, 409)}
)
@versioning.versions(minimal=1)
async def delete_existing_user(
        user: schemas.User,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing user model.

    This operation will delete the user aliases, but no user history or transactions.

    A 404 error will be returned if the user's `id` doesn't exist.
    A 409 error will be returned if the object is not up-to-date, the balance
    of the user is not zero or if there are any open refund requests or communisms
    that were either created by that user or which this user participates in.
    """

    def hook(model, *_):
        if model.balance != 0:
            info = ""
            if model.voucher_id and model.external:
                info = f" User {model.voucher_id} vouches for this user and may handle this."
            raise Conflict(f"Balance of {user.name} is not zero.{info} Can't delete user.", str(user))

        active_created_refunds = local.session.query(models.Refund).filter_by(
            active=True, creator_id=model.id
        ).all()
        if active_created_refunds:
            raise Conflict(
                f"User {user.name} has at least one active refund requests. Can't delete user.",
                str(active_created_refunds)
            )

        active_created_communisms = local.session.query(models.Communism).filter_by(
            active=True, creator_id=model.id
        ).all()
        if active_created_communisms:
            raise Conflict(
                f"User {user.name} has created at least one active communism. Can't delete user.",
                str(active_created_communisms)
            )

        for communism in local.session.query(models.Communism).filter_by(active=True).all():
            for participant in communism.participants:
                participant: models.CommunismUsers
                if participant.user_id == model.id:
                    if participant.quantity == 0:
                        logger.warning(f"Quantity 0 for {participant} of {communism}.")
                    raise Conflict(
                        f"User {user.name} is participant of at least one active communism. Can't delete user.",
                        str(participant)
                    )

    return await helpers.delete_one_of_model(
        user.id,
        models.User,
        local,
        schema=user,
        logger=logger,
        hook_func=hook
    )


@router.get(
    "/{user_id}",
    response_model=schemas.User,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_user_by_id(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the internal model of the user specified by its user ID.

    A 404 error will be returned in case the user ID is unknown.
    """

    return await helpers.get_one_of_model(user_id, models.User, local)
