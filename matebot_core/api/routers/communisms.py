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
from ...misc.transactions import create_many_to_one_transaction_by_total
from ... import schemas


logger = logging.getLogger(__name__)


def _compress_participants(participants: List[schemas.CommunismUserBinding]) -> List[schemas.CommunismUserBinding]:
    compressed = {}
    for binding in participants:
        if binding.user_id not in compressed:
            compressed[binding.user_id] = 0
        compressed[binding.user_id] += binding.quantity
    return [schemas.CommunismUserBinding(user_id=k, quantity=v) for k, v in compressed.items()]


async def _check_participants(participants: List[schemas.CommunismUserBinding], local: LocalRequestData):
    def restrict_community_user(special_flag: bool):
        if special_flag:
            raise Conflict("The community user can't participate in communisms.")

    invalid_participant_entries = [
        (k, v) for k, v in {
            p.user_id: await helpers.return_one(p.user_id, models.User, local.session)
            for p in participants
        }.items()
        if not v.active or (v.external and v.voucher_user is None) or restrict_community_user(v.special)
    ]
    if invalid_participant_entries:
        raise BadRequest(
            f"Disabled users or externals without voucher can't participate in communisms. "
            f"{len(invalid_participant_entries)} proposed participants are disabled or external.",
            str(invalid_participant_entries)
        )


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
    responses={k: {"model": schemas.APIError} for k in (400, 404, 409)}
)
@versioning.versions(minimal=1)
async def create_new_communism(
        communism: schemas.CommunismCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new communism based on the specified data

    * `400`: if the creator is an external user without voucher or has been
        disabled or if the creator user specification couldn't be resolved
    * `404`: if the user ID of the creator user or any mentioned participant is unknown
    * `409`: if the community user is part of the list of participants
    """

    creator = await helpers.resolve_user_spec(communism.creator, local)
    if creator.special:
        raise Conflict("The community user can't open communisms.")
    if not creator.active:
        raise BadRequest("Your user account was deleted. Therefore, you can't create communisms.")
    if creator.external and creator.voucher_user is None:
        raise BadRequest("You can't create communisms without having a voucher user.")

    model = models.Communism(
        amount=communism.amount,
        description=communism.description,
        creator=creator,
        active=True,
        participants=[models.CommunismUsers(user_id=creator.id, quantity=1)]
    )

    return await helpers.create_new_of_model(model, local, logger)


@router.post(
    "/communisms/abort",
    tags=["Communisms"],
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def abort_open_communism(
        body: schemas.IdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an open communism (closing it without performing transactions)

    * `400`: if the communism is already closed
    * `404`: if the communism ID is unknown
    """

    model = await helpers.return_one(body.id, models.Communism, local.session)

    if not model.active:
        raise BadRequest("Updating an already closed communism is not possible.", detail=str(model))

    model.active = False
    logger.debug(f"Aborting communism {model}")
    return await helpers.update_model(model, local, logger)


@router.post(
    "/communisms/close",
    tags=["Communisms"],
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def close_open_communism(
        body: schemas.IdBody,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Close an open communism (closing it with performing transactions)

    * `400`: if the communism is already closed
    * `404`: if the communism ID is unknown
    """

    model = await helpers.return_one(body.id, models.Communism, local.session)
    if not model.active:
        raise BadRequest("Updating an already closed communism is not possible.", detail=str(model))

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
            "communism[{n}]: {reason}",
            local.tasks
        )

    model.multi_transaction = m
    logger.debug(f"Closing communism {model} (created multi transaction {m} with {len(ts)} parts)")
    return await helpers.update_model(model, local, logger)


@router.post(
    "/communisms/setParticipants",
    tags=["Communisms"],
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def set_participants_of_open_communism(
        body: schemas.CommunismUserUpdate,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Set the participants of an open communism

    * `400`: if the communism is already closed or if any participant
        is an external user without voucher or a disabled user
    * `404`: if the communism ID or the user ID of any mentioned participant is unknown
    * `409`: if the community user is part of the participants
    """

    model = await helpers.return_one(body.id, models.Communism, local.session)

    if not model.active:
        raise BadRequest("Updating an already closed communism is not possible.", detail=str(model))

    participants = _compress_participants(body.participants)
    await _check_participants(participants, local)

    remaining = list(participants)[:]
    for c_u in model.participants:
        for p in participants:
            if c_u.user_id == p.user_id:
                c_u.quantity = p.quantity
                remaining.remove(p)
                break
        else:
            local.session.delete(c_u)
    for p in remaining:
        local.session.add(models.CommunismUsers(communism_id=model.id, user_id=p.user_id, quantity=p.quantity))

    return await helpers.update_model(model, local, logger)
