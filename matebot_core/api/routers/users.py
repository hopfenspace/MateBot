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
from ...misc.notifier import Callback
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)


@router.get("/users", tags=["Users"], response_model=List[schemas.User])
@versioning.versions(1)
async def search_for_users(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        name: Optional[pydantic.constr(max_length=255)] = None,
        community: Optional[bool] = None,
        permission: Optional[bool] = None,
        active: Optional[bool] = None,
        external: Optional[bool] = None,
        voucher_id: Optional[pydantic.NonNegativeInt] = None,
        alias_id: Optional[pydantic.NonNegativeInt] = None,
        alias_username: Optional[pydantic.constr(max_length=255)] = None,
        alias_confirmed: Optional[bool] = None,
        alias_application: Optional[pydantic.constr(max_length=255)] = None,
        alias_application_id: Optional[pydantic.NonNegativeInt] = None,
        limit: Optional[pydantic.NonNegativeInt] = None,
        page: Optional[pydantic.NonNegativeInt] = None,
        descending: Optional[bool] = False,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all users that fulfill *all* constraints given as query parameters

    Query parameters prefixed with `alias_` are treated as filters for
    users that have an alias fulfilling the given parameters. If a user
    model has no aliases at all, it will be filtered out if at least
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
            if alias_application is not None and a.application.name != alias_application:
                continue
            if alias_application_id is not None and a.application_id != alias_application_id:
                continue
            return True
        return not user.aliases and all(
            obj is None for obj in [alias_username, alias_confirmed, alias_application, alias_application_id]
        )

    return helpers.search_models(
        models.User,
        local,
        specialized_item_filter=extended_filter,
        limit=limit,
        page=page,
        descending=descending,
        id=id,
        name=name,
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
async def create_new_user(request: schemas.UserCreation, local: LocalRequestData = Depends(LocalRequestData)):
    """
    Create a new "empty" user account with zero balance
    """

    if local.session.query(models.User).filter_by(name=request.name).all():
        raise BadRequest(f"Username {request.name!r} is not available.")
    model = models.User(
        balance=0,
        name=request.name,
        permission=False,
        active=True,
        external=True,
        voucher_id=None
    )
    local.session.add(model)
    local.session.commit()
    return model.schema


@router.post(
    "/users/dropInternal",
    tags=["Users"],
    response_model=schemas.User,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
)
@versioning.versions(1)
async def drop_internal_privilege(
        body: schemas.UserPrivilegeDrop,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Drop the internal privilege of the specified user

    * `400`: if the user specification couldn't be resolved, the issuer
        doesn't equal the user or the user is already an external
    * `409`: if an inactive user or the community user was targeted
    """

    def hook(model):
        if model.external:
            raise BadRequest("You are an external user, you can't drop such privileges.")
        model.external = True
        model.permission = False
        return model

    user = await helpers.drop_user_privileges_impl(body.user, body.issuer, local, hook)
    Callback.push(schemas.EventType.USER_UPDATED, {"id": user.id})
    return user.schema


@router.post(
    "/users/dropPermission",
    tags=["Users"],
    response_model=schemas.User,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
)
@versioning.versions(1)
async def drop_permission_privilege(
        body: schemas.UserPrivilegeDrop,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Drop the vote permission privilege of the specified user

    * `400`: if the user specification couldn't be resolved, the issuer
        doesn't equal the user or the user doesn't have that privilege
    * `409`: if an inactive user or the community user was targeted
    """

    def hook(model):
        if not model.permission:
            raise BadRequest("You don't have extended permissions and therefore can't drop them.")
        model.permission = False
        return model

    user = await helpers.drop_user_privileges_impl(body.user, body.issuer, local, hook)
    Callback.push(schemas.EventType.USER_UPDATED, {"id": user.id})
    return user.schema


@router.post(
    "/users/setName",
    tags=["Users"],
    response_model=schemas.User,
    responses={400: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def set_global_username(
        update: schemas.UsernameUpdateRequest,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Set the globally unique name of a particular user

    * `400`: if the user is disabled or the username is already taken
    """

    issuer = await helpers.resolve_user_spec(update.issuer, local)
    if not issuer.active:
        raise BadRequest("This user account is disabled.")
    if local.session.query(models.User).filter_by(name=update.name).all():
        raise BadRequest(f"Username {update.name!r} is not available.")
    issuer.name = update.name
    local.session.add(issuer)
    local.session.commit()
    Callback.push(schemas.EventType.USER_UPDATED, {"id": issuer.id})
    return issuer.schema


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
    issuer = await helpers.resolve_user_spec(update.issuer, local)

    if debtor.special:
        raise BadRequest("Nobody can vouch for the community user.")
    if voucher and voucher.special:
        raise Conflict("The community user can't vouch for anyone.")
    if voucher and issuer != voucher:
        raise BadRequest("You can't let someone else vouch on your behalf.")

    if debtor.voucher_user is not None and voucher and debtor.voucher_user != voucher:
        raise BadRequest("This user already has a voucher, you can't vouch for it.")

    if debtor == voucher:
        raise BadRequest("You can't vouch for yourself.")
    if debtor == issuer:
        raise BadRequest("You can't change your own vouching state, you need another user to do that.")
    if not debtor.external:
        raise BadRequest("You can't vouch for this user, since it's an internal user.")
    if issuer.external or not issuer.active:
        raise BadRequest("You can't vouch for other users.")
    if voucher and voucher.external:
        raise BadRequest("You can't vouch for anyone else, since you are an external user yourself.")
    if voucher and len(voucher.vouching_for) >= local.config.general.max_parallel_debtors:
        raise BadRequest(f"You can't vouch for more than {local.config.general.max_parallel_debtors} in parallel.")

    transaction = None
    if debtor.voucher_user is not None and voucher is None:
        if debtor.balance > 0:
            transaction = transactions.create_transaction(
                debtor,
                debtor.voucher_user,
                abs(debtor.balance),
                "vouch: stopping vouching",
                local.session,
                logger
            )
        elif debtor.balance < 0:
            transaction = transactions.create_transaction(
                debtor.voucher_user,
                debtor,
                abs(debtor.balance),
                "vouch: stopping vouching",
                local.session,
                logger
            )

    debtor.voucher_user = voucher
    local.session.add(debtor)
    local.session.commit()
    Callback.push(
        schemas.EventType.VOUCHER_UPDATED,
        {"id": debtor.id, "voucher": voucher and voucher.id, "transaction": transaction and transaction.id}
    )
    return schemas.VoucherUpdateResponse(
        debtor=debtor.schema,
        voucher=voucher and voucher.schema,
        transaction=transaction and transaction.schema
    )


@router.post(
    "/users/delete",
    tags=["Users"],
    response_model=schemas.User,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
)
@versioning.versions(1)
async def softly_delete_user_permanently(
        body: schemas.IssuerIdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Disable a user account, without the possibility to effectively re-enable it (= deletion)

    This operation will delete the user aliases, but no user history or
    transactions. If the user account has any positive balance left, it will be
    moved to the community. Users with negative balance can't be deleted.

    * `400`: if the given user wasn't found, actively vouches for someone
        else, has a negative balance, has created / participates in any
        open communisms or refund requests or is already disabled
        or if the issuer is not permitted to perform the operation
    """

    model = await helpers.return_one(body.id, models.User, local.session)
    issuer = await helpers.resolve_user_spec(body.issuer, local)

    if not model.active:
        raise BadRequest("This user account is already disabled.")
    if model.special:
        raise Conflict("The community user can't be disabled.")
    if model.id != issuer.id:
        raise BadRequest("A user can only disable itself, not somebody else.", detail=str(issuer))

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
            logger
        )

    # Deleting aliases using this helper method is preferred to trigger callbacks correctly
    for alias in model.aliases:
        await helpers.delete_one_of_model(alias.id, models.Alias, local, logger=logger)

    model.aliases = []
    model.active = False
    local.session.add(model)
    local.session.commit()
    Callback.push(schemas.EventType.USER_SOFTLY_DELETED, {"id": model.id})
    return model.schema
