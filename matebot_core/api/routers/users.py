"""
MateBot router module for /users requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import Conflict, MissingImplementation
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
@versioning.min_version(1)
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
@versioning.min_version(1)
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
@versioning.min_version(1)
async def update_existing_user(
        user: schemas.User,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing user model identified by the `user_id`.

    A 404 error will be returned if the `user_id` is not known. A 409 error
    will be returned when some of the following fields have been changed
    compared to the internal user state: `balance`, `created`, `accessed`.
    """

    raise MissingImplementation("update_existing_user")


@router.delete(
    "",
    status_code=204,
    responses={
        404: {"model": schemas.APIError},
        409: {"model": schemas.APIError},
        412: {"model": schemas.APIError}
    }
)
@versioning.min_version(1)
async def delete_existing_user(
        user: schemas.User,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing user model.

    This operation will delete the user aliases, but no user history or transactions.

    A 404 error will be returned if the user's `id` doesn't exist.
    A 409 error will be returned if the balance of the user is not zero
    or if there are any open refund requests or communisms that were
    either created by that user or which this user participates in.
    A 412 error will be returned if the conditional request fails.
    """

    def hook(model, *args):
        if model.balance != 0:
            raise Conflict(f"Balance of {user.name} is not zero. Can't delete user.", str(user))

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

        raise MissingImplementation("delete_existing_user_hook_check_communism_participants")

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


@router.delete(
    "/{user_id}",
    status_code=204,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def delete_existing_user_by_id(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Delete an existing user model identified by its user ID.

    A 409 error will be returned if there are any open refund requests or
    communisms that were either created by that user or which this user
    participates in. Note that a balance other than zero is acceptable
    in this endpoint, as long as there's some other user vouching for
    the user in question. The voucher will either receive the remaining
    money or has to pay remaining bills. This operation will also
    delete any user aliases, but no user history or transactions.
    A 404 error will be returned in case the user ID is unknown.
    """

    raise MissingImplementation("delete_existing_user_by_id")
