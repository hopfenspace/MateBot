"""
MateBot router module for /users requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import APIRouter, Depends

from ..base import BadRequest, Conflict, InternalServerException
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...misc import transactions
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/users", tags=["Users"])


@router.get(
    "",
    response_model=List[schemas.User]
)
@versioning.versions(1)
async def get_all_users(
        user_id: Optional[pydantic.NonNegativeInt] = None,
        user_name: Optional[pydantic.constr(max_length=255)] = None,
        user_permission: Optional[bool] = None,
        user_active: Optional[bool] = None,
        user_external: Optional[bool] = None,
        user_voucher_id: Optional[pydantic.NonNegativeInt] = None,
        alias_id: Optional[pydantic.NonNegativeInt] = None,
        alias_app_username: Optional[pydantic.constr(max_length=255)] = None,
        alias_confirmed: Optional[bool] = None,
        alias_application_id: Optional[pydantic.NonNegativeInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all users that fulfill *all* constraints given as query parameters

    Query parameters prefixed with `user_` are treated as direct filters on
    the user model. Query parameters prefixed with `alias_` are treated as
    filters for users that have an alias fulfilling the given parameters. If
    a user model has no aliases at all, it will be filtered out if at least
    one `alias_` query parameter has been set. If no query parameters are
    given, this endpoint will just return all currently known user models.
    """

    query = local.session.query(models.User)
    if user_id is not None:
        query = query.filter_by(id=user_id)
    if user_name is not None:
        query = query.filter_by(name=user_name)
    if user_permission is not None:
        query = query.filter_by(permission=user_permission)
    if user_active is not None:
        query = query.filter_by(active=user_active)
    if user_external is not None:
        query = query.filter_by(external=user_external)
    if user_voucher_id is not None:
        query = query.filter_by(external=True, voucher_id=user_voucher_id)

    hits = []
    users = [u for u in query.all() if (alias_id is None or alias_id in [a.id for a in u.aliases])]
    for u in users:
        valid_alias = False
        for a in u.aliases:
            if alias_app_username is not None and a.app_username != alias_app_username:
                continue
            if alias_confirmed is not None and a.confirmed != alias_confirmed:
                continue
            if alias_application_id is not None and a.application_id != alias_application_id:
                continue
            valid_alias = True
        if valid_alias or (not u.aliases and [alias_app_username, alias_confirmed, alias_application_id] == [None] * 3):
            hits.append(u)

    return [m.schema for m in hits]


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
    values["active"] = True
    model = models.User(**values)
    return await helpers.create_new_of_model(model, local, logger, "/users/{}", True)


@router.put(
    "",
    response_model=schemas.User,
    responses={k: {"model": schemas.APIError} for k in (404, 409)}
)
@versioning.versions(minimal=1)
async def update_existing_user(
        user: schemas.User,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Update an existing user model identified by the `user_id`.

    This endpoint only allows to change the name, permissions and
    external flag of a user. Use the specialised POST endpoints for
    other user-related actions like disabling or vouching.

    A 404 error will be returned if the user ID is not known.
    A 409 error will be returned if an inactive or the special
    user was changed or an external user was granted permissions.
    """

    model = await helpers.return_one(user.id, models.User, local.session)

    if not model.active:
        raise Conflict(f"User {model.id} is disabled and can't be updated.", str(user))
    if model.special:
        raise Conflict("The community user can't be updated via this endpoint.", str(user))
    if user.external and user.permission:
        raise Conflict("An external user can't have extended permissions", str(user))

    model.name = user.name
    model.permission = user.permission
    model.external = user.external

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)


@router.get(
    "/community",
    response_model=schemas.User
)
@versioning.versions(1)
async def get_community_user(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return the user model of the community user.
    """

    objs = await helpers.return_all(models.User, local.session, special=True)
    if len(objs) != 1:
        raise InternalServerException("Multiple community users found. Please file a bug report.", str(objs))
    return objs[0].schema


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


@router.post(
    "/setVoucher",
    response_model=schemas.VoucherUpdateResponse,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(1)
async def set_voucher_of_user(
        update: schemas.VoucherUpdateRequest,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Set (or unset) the voucher of a particular debtor user

    This endpoint will adjust the balance of the debtor user accordingly by creating
    a new transaction, if the voucher has been changed to None (= unset).

    A 400 error will be returned if changing the voucher is not possible for
    various reasons (e.g. someone already vouches for the particular user).
    A 404 error will be returned in case any user ID is unknown.
    A 409 error will be returned if the community user was used in the query.
    """

    debtor = await helpers.return_one(update.debtor, models.User, local.session)
    voucher = update.voucher and await helpers.return_one(update.voucher, models.User, local.session)

    if debtor.special:
        raise Conflict("Nobody can vouch for the community user.")
    if voucher and voucher.special:
        raise Conflict("The community user can't vouch for anyone.")

    if debtor.voucher_user is not None and voucher and debtor.voucher_user != voucher:
        raise BadRequest(f"Someone already vouches for {debtor.name}, you can't vouch for it.", str(debtor))

    if debtor == voucher:
        raise BadRequest("You can't vouch for yourself.", str(voucher))
    if not debtor.external:
        raise BadRequest("You can't vouch for {debtor.name}, since it's an internal user.", str(debtor))

    transaction = None
    if debtor.voucher_user is not None and voucher is None:
        if debtor.balance > 0:
            transaction = transactions.create_transaction(
                debtor,
                debtor.voucher_user,
                abs(debtor.balance),
                "vouch: stopping vouching",
                local.session,
                logger,
                local.tasks
            )
        elif debtor.balance < 0:
            transaction = transactions.create_transaction(
                debtor.voucher_user,
                debtor,
                abs(debtor.balance),
                "vouch: stopping vouching",
                local.session,
                logger,
                local.tasks
            )

    debtor.voucher_user = voucher
    await helpers.update_model(debtor, local, logger, helpers.ReturnType.NONE)
    return schemas.VoucherUpdateResponse(
        debtor=debtor,
        voucher=voucher,
        transaction=transaction
    )


@router.post(
    "/disable/{user_id}",
    response_model=schemas.User,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(1)
async def disable_user_permanently(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Disable a user account, without the possibility to effectively re-enable it (= deletion)

    This operation will delete the user aliases, but no user history or transactions.

    A 400 error will be returned if the given user actively vouches for
    someone else, has a non-zero balance or has created / participates
    in any open communisms or refund requests.
    A 404 error will be returned if the `user_id` is not found.
    A 409 error will be returned if an already inactive or the special user was given.
    """

    model = await helpers.return_one(user_id, models.User, local.session)

    if not model.active:
        raise Conflict(f"User {model.id} is already disabled.", str(model))
    if model.special:
        raise Conflict("The community user can't be disabled.", str(model))

    if local.session.query(models.Communism).filter_by(creator=model, active=True).all():
        raise BadRequest(
            "You have created at least one communism which is still open. "
            "Therefore, your user account can't be deleted."
        )

    for communism in local.session.query(models.Communism).filter_by(active=True).all():
        for participant in communism.participants:
            if participant.user_id == model.id:
                raise BadRequest(
                    "You are currently participating in an open communism. "
                    "Therefore, your user account can't be deleted."
                )

    if local.session.query(models.Refund).filter_by(creator=model, active=True).all():
        raise BadRequest(
            "You have created at least one refund request which is still open. "
            "Therefore, your user account can't be deleted."
        )

    if not model.external and local.session.query(models.User).filter_by(voucher=model, active=True).all():
        raise BadRequest(
            "You are currently vouching for at least one other user. "
            "Therefore, your user account can't be deleted."
        )

    if model.balance != 0:
        info = ""
        if model.voucher and model.external:
            info = f" User {model.voucher.name!r} vouches for you and may help you to handle this."
        raise BadRequest(
            f"Your balance is not zero. You need a zero balance before you can delete your user account.{info}"
        )

    # Deleting aliases using this helper method is preferred to trigger callbacks correctly
    for alias in model.aliases:
        await helpers.delete_one_of_model(
            alias.id,
            models.Alias,
            local,
            logger=logger
        )
    model.aliases = []
    model.active = False

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)
