"""
MateBot router module for /communisms requests
"""

import logging
from typing import List, Optional

import pydantic
from fastapi import Depends

from ._router import router
from ..base import BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.notifier import Callback
from ...misc.transactions import create_many_to_one_transaction_by_total
from ... import schemas


logger = logging.getLogger(__name__)


async def _update_participation(
        communism: models.Communism,
        user: models.User,
        quantity_diff: int,
        local: LocalRequestData
) -> schemas.Communism:
    if not communism.active:
        raise BadRequest("Updating an already closed communism is not possible.", detail=str(communism))
    if not user.active:
        raise BadRequest(f"{user.name} is a disabled user, it can't participate in communisms.", detail=str(user))
    if user.external and user.voucher_user is None:
        raise BadRequest(f"{user.name} is an external user without voucher.")
    if user.special:
        raise Conflict("The community user can't participate in communisms.")
    if quantity_diff == 0:
        return communism.schema

    for communism_user in communism.participants:
        if communism_user.user_id == user.id:
            if quantity_diff < 0 and abs(quantity_diff) < communism_user.quantity:
                communism_user.quantity -= abs(quantity_diff)
            elif quantity_diff < 0 and abs(quantity_diff) == communism_user.quantity:
                local.session.delete(communism_user)
            elif quantity_diff < 0:
                raise BadRequest(f"You can't participate less than zero times in communisms.")
            elif quantity_diff > 0:
                communism_user.quantity += quantity_diff
            break
    else:
        if quantity_diff > 0:
            local.session.add(models.CommunismUsers(communism_id=communism.id, user_id=user.id, quantity=quantity_diff))
        else:
            raise BadRequest(f"You don't participate in this communism, you can't leave it.")

    local.session.add(communism)
    local.session.commit()

    Callback.push(
        schemas.EventType.COMMUNISM_UPDATED,
        {"id": communism.id, "participants": sum([p.quantity for p in communism.participants])}
    )
    return communism.schema


@router.get("/communisms", tags=["Communisms"], response_model=List[schemas.Communism])
@versioning.versions(minimal=1)
async def search_for_communisms(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        active: Optional[bool] = None,
        amount: Optional[pydantic.PositiveInt] = None,
        description: Optional[pydantic.constr(max_length=255)] = None,
        creator_id: Optional[pydantic.NonNegativeInt] = None,
        participant_id: Optional[pydantic.NonNegativeInt] = None,
        total_participants: Optional[pydantic.NonNegativeInt] = None,
        unique_participants: Optional[pydantic.NonNegativeInt] = None,
        limit: Optional[pydantic.NonNegativeInt] = None,
        page: Optional[pydantic.NonNegativeInt] = None,
        descending: Optional[bool] = False,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all communisms that fulfill *all* constraints given as query parameters
    """

    def extended_filter(communism: models.Communism) -> bool:
        if participant_id is not None and participant_id not in [p.user_id for p in communism.participants]:
            return False
        if total_participants is not None and total_participants != sum(p.quantity for p in communism.participants):
            return False
        if unique_participants is not None and unique_participants != len({p.user_id for p in communism.participants}):
            return False
        return True

    return helpers.search_models(
        models.Communism,
        local,
        specialized_item_filter=extended_filter,
        limit=limit,
        page=page,
        descending=descending,
        id=id,
        active=active,
        amount=amount,
        description=description,
        creator_id=creator_id
    )


@router.post(
    "/communisms",
    tags=["Communisms"],
    status_code=201,
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
)
@versioning.versions(minimal=1)
async def create_new_communism(
        communism: schemas.CommunismCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new communism based on the specified data

    * `400`: if the creator or any participant is an external user
        without voucher, if the creator or any participant is disabled,
        if the creator user specification couldn't be resolved or the user
        ID of the creator user or any mentioned participant is unknown
    * `409`: if the community user is part of the list of participants
    """

    creator = await helpers.resolve_user_spec(communism.creator, local)
    if creator.special:
        raise Conflict("The community user can't open communisms.")
    if not creator.active:
        raise BadRequest("This user account has been deleted. Therefore, you can't create communisms.")
    if creator.external and creator.voucher_user is None:
        raise BadRequest("You can't create communisms without having a voucher user.")

    model = models.Communism(
        amount=communism.amount,
        description=communism.description,
        creator=creator,
        active=True,
        participants=[models.CommunismUsers(user_id=creator.id, quantity=1)]
    )
    local.session.add(model)
    local.session.commit()
    Callback.push(
        schemas.EventType.COMMUNISM_CREATED,
        {"id": model.id, "user": model.creator.id, "amount": model.amount, "participants": 1}
    )
    return model.schema


@router.post(
    "/communisms/abort",
    tags=["Communisms"],
    response_model=schemas.Communism,
    responses={400: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def abort_open_communism(
        body: schemas.IssuerIdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an open communism (closing it without performing transactions)

    * `400`: if the communism is unknown or already closed or
        if the issuer is not permitted to perform the operation
    """

    model = await helpers.return_one(body.id, models.Communism, local.session)
    issuer = await helpers.resolve_user_spec(body.issuer, local)

    if not model.active:
        raise BadRequest("Updating an already closed communism is not possible.", detail=str(model))
    if model.creator.id != issuer.id:
        raise BadRequest("Only the creator of a communism is allowed to abort it.", detail=str(issuer))

    model.active = False
    logger.debug(f"Aborting communism {model}")
    local.session.add(model)
    local.session.commit()

    total_participants = sum([p.quantity for p in model.participants])
    Callback.push(
        schemas.EventType.COMMUNISM_CLOSED,
        {"id": model.id, "aborted": True, "transactions": 0, "participants": total_participants}
    )
    return model.schema


@router.post(
    "/communisms/close",
    tags=["Communisms"],
    response_model=schemas.Communism,
    responses={400: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def close_open_communism(
        body: schemas.IssuerIdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Close an open communism (closing it with performing transactions)

    * `400`: if the communism is unknown or already closed or
        if the issuer is not permitted to perform the operation
    """

    model = await helpers.return_one(body.id, models.Communism, local.session)
    issuer = await helpers.resolve_user_spec(body.issuer, local)

    if not model.active:
        raise BadRequest("Updating an already closed communism is not possible.", detail=str(model))
    if model.creator.id != issuer.id:
        raise BadRequest("Only the creator of a communism is allowed to close it.", detail=str(issuer))

    model.active = False
    m, ts = None, []
    if sum(p.quantity for p in model.participants if p.user_id != model.creator_id) > 0:
        m, ts = create_many_to_one_transaction_by_total(
            [(p.user, p.quantity) for p in model.participants],
            model.creator,
            model.amount,
            model.description,
            local.session,
            logger,
            "communism[{n}]: {reason}"
        )

    model.multi_transaction = m
    logger.debug(f"Closing communism {model} (created multi transaction {m} with {len(ts)} parts)")
    local.session.add(model)
    local.session.commit()

    transactions = (m and len(model.multi_transaction.transactions)) or 0
    total_participants = sum([p.quantity for p in model.participants])
    Callback.push(
        schemas.EventType.COMMUNISM_CLOSED,
        {"id": model.id, "aborted": False, "transactions": transactions, "participants": total_participants}
    )
    return model.schema


@router.post(
    "/communisms/increaseParticipation",
    tags=["Communisms"],
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 409)}
)
@versioning.versions(1)
async def increase_participation_in_open_communism(
        body: schemas.CommunismParticipationUpdate,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Increase the participation of a single user by 1 for an open communism

    * `400`: if the communism is already closed, if any participant
        is an external user without voucher or a disabled user or if
        any of the participant user specs or the communism ID is unknown
    * `409`: if the community user is the user selected for participation
    """

    return await _update_participation(
        await helpers.return_one(body.id, models.Communism, local.session),
        await helpers.resolve_user_spec(body.user, local),
        1,
        local
    )


@router.post(
    "/communisms/decreaseParticipation",
    tags=["Communisms"],
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(1)
async def decrease_participation_in_open_communism(
        body: schemas.CommunismParticipationUpdate,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Decrease the participation of a single user by 1 for an open communism

    * `400`: if the communism is already closed, if any participant
        is an external user without voucher or a disabled user or if
        any of the participant user specs or the communism ID is unknown or
        there was an attempt to leave a communism without prior participation
    * `409`: if the community user is the user selected for participation
    """

    return await _update_participation(
        await helpers.return_one(body.id, models.Communism, local.session),
        await helpers.resolve_user_spec(body.user, local),
        -1,
        local
    )
