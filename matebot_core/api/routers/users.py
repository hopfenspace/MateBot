"""
MateBot router module for /users requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import Depends

from ._router import router
from ..base import BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...misc import transactions
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)


@router.get("/users", tags=["Users"], response_model=List[schemas.User])
@versioning.versions(1)
async def search_for_users(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        community: Optional[bool] = None,
        permission: Optional[bool] = None,
        active: Optional[bool] = None,
        external: Optional[bool] = None,
        voucher_id: Optional[pydantic.NonNegativeInt] = None,
        alias_id: Optional[pydantic.NonNegativeInt] = None,
        alias_username: Optional[pydantic.constr(max_length=255)] = None,
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

    def extended_filter(user: models.User) -> bool:
        if community is not None and not community and user.special:
            return False
        if not (alias_id is None or alias_id in [a.id for a in user.aliases]):
            return False
        for a in user.aliases:
            if alias_username is not None and a.username != alias_username:
                continue
            if alias_confirmed is not None and a.confirmed != alias_confirmed:
                continue
            if alias_application_id is not None and a.application_id != alias_application_id:
                continue
            return True
        return not user.aliases and [alias_username, alias_confirmed, alias_application_id] == [None] * 3

    return helpers.search_models(
        models.User,
        local,
        specialized_item_filter=extended_filter,
        id=id,
        special=community or None,
        permission=permission,
        active=active,
        external=external,
        voucher_id=voucher_id
    )


@router.post(
    "/users",
    tags=["Users"],
    status_code=201,
    response_model=schemas.User
)
@versioning.versions(minimal=1)
async def create_new_user(
        user: schemas.UserCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new "empty" user account with zero balance
    """

    values = user.dict()
    values["active"] = True
    model = models.User(**values)
    return await helpers.create_new_of_model(model, local, logger)


@router.post(
    "/users/setFlags",
    tags=["Users"],
    response_model=schemas.User,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
)
@versioning.versions(minimal=1)
async def set_flags_of_user(
        change: schemas.UserFlagsChangeRequest,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Set & unset the flags of an existing user

    * `400`: if the user specification couldn't be resolved
    * `409`: if an inactive user was changed or if both
        `external=true` and `permission=true` were set
    """

    model = await helpers.resolve_user_spec(change.user, local)

    if not model.active:
        raise Conflict("This user account is disabled and can't be updated.")
    if change.external and change.permission:
        raise Conflict("An external user can't get extended permissions.")

    if change.external is not None:
        model.external = change.external
    if change.permission is not None:
        model.permission = change.permission
    return await helpers.update_model(model, local, logger)


@router.post(
    "/users/setVoucher",
    tags=["Users"],
    response_model=schemas.VoucherUpdateResponse,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
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

    * `400`: if changing the voucher is not possible for various reasons
        (e.g. someone already vouches for the particular user) or if
        the debtor or voucher user specifications couldn't be resolved
    * `409`: if the community user was used in the query
    """

    debtor = await helpers.resolve_user_spec(update.debtor, local)
    voucher = update.voucher and await helpers.resolve_user_spec(update.voucher, local)

    if debtor.special:
        raise BadRequest("Nobody can vouch for the community user.")
    if voucher and voucher.special:
        raise Conflict("The community user can't vouch for anyone.")

    if debtor.voucher_user is not None and voucher and debtor.voucher_user != voucher:
        raise BadRequest("This user already has a voucher, you can't vouch for it.")

    if debtor == voucher:
        raise BadRequest("You can't vouch for yourself.")
    if not debtor.external:
        raise BadRequest("You can't vouch for this user, since it's an internal user.")

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
    await helpers.update_model(debtor, local, logger)
    return schemas.VoucherUpdateResponse(
        debtor=debtor,
        voucher=voucher,
        transaction=transaction
    )


@router.post(
    "/users/disable",
    tags=["Users"],
    response_model=schemas.User,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
)
@versioning.versions(1)
async def disable_user_permanently(
        body: schemas.IdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Disable a user account, without the possibility to effectively re-enable it (= deletion)

    This operation will delete the user aliases, but no user history or
    transactions. If the user account has any positive balance left, it will be
    moved to the community. Users with negative balance can't be deleted.

    * `400`: if the given user actively vouches for someone else,
        has a negative balance, has created / participates in any
        open communisms or refund requests or is already disabled
        or if the user ID wasn't found
    * `409`: if the community user was given
    """

    model = await helpers.return_one(body.id, models.User, local.session)

    if not model.active:
        raise BadRequest("This user account is already disabled.")
    if model.special:
        raise Conflict("The community user can't be disabled.")

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

    if not model.external and local.session.query(models.User).filter_by(voucher_user=model, active=True).all():
        raise BadRequest(
            "You are currently vouching for at least one other user. "
            "Therefore, your user account can't be deleted."
        )

    if model.balance < 0:
        info = ""
        if model.voucher_user and model.external:
            info = " You have a voucher who may help you to handle this."
        raise BadRequest(
            f"Your balance is negative. You need a non-negative balance "
            f"before you can delete your user account.{info}"
        )

    if model.balance > 0:
        community = local.session.query(models.User).filter_by(special=True).first()
        if community is None:
            raise RuntimeError("No community user found. Please make sure to setup the DB correctly.")
        transactions.create_transaction(
            model,
            community,
            model.balance,
            f"permanent deletion of user account {model.id}",
            local.session,
            logger,
            local.tasks
        )

    # Deleting aliases using this helper method is preferred to trigger callbacks correctly
    for alias in model.aliases:
        await helpers.delete_one_of_model(alias.id, models.Alias, local, logger=logger)
    model.aliases = []
    model.active = False

    return await helpers.update_model(model, local, logger)
