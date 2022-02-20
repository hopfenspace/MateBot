"""
MateBot router module for /communisms requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import BadRequest, Conflict
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ...misc.transactions import create_many_to_one_transaction_by_total
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/communisms", tags=["Communisms"])


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


@router.get(
    "",
    response_model=List[schemas.Communism]
)
@versioning.versions(minimal=1)
async def get_all_communisms(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all communisms in the system.
    """

    return await helpers.get_all_of_model(models.Communism, local)


@router.post(
    "",
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

    A 400 error will be returned if the creator or any participant is an external
    user without voucher, or if the creator or any participant is disabled.
    A 404 error will be returned if the user ID of the
    creator user or any mentioned participant is unknown.
    A 409 error will be returned if the community user is part of it.
    """

    creator = await helpers.return_one(communism.creator_id, models.User, local.session)
    if creator.special:
        raise Conflict("The community user can't open communisms.")
    if not creator.active:
        raise BadRequest("Your user account was deleted. Therefore, you can't create communisms.")
    if creator.external and creator.voucher_user is None:
        raise BadRequest("You can't create communisms without having a voucher user.")

    participants = _compress_participants(communism.participants)
    await _check_participants(participants, local)

    model = models.Communism(
        amount=communism.amount,
        description=communism.description,
        creator=creator,
        active=communism.active,
        participants=[
            models.CommunismUsers(user_id=p.user_id, quantity=p.quantity)
            for p in participants
        ]
    )

    return await helpers.create_new_of_model(model, local, logger)


@router.get(
    "/{communism_id}",
    response_model=schemas.Communism,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_communism_by_id(
        communism_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return an existing communism by its `communism_id`.

    A 404 error will be returned if the specified ID was not found.
    """

    return await helpers.get_one_of_model(communism_id, models.Communism, local)


@router.get(
    "/creator/{user_id}",
    response_model=List[schemas.Communism],
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_communisms_by_creator(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return a list of all communisms which have been created by the specified user

    A 404 error will be returned if the user ID is unknown.
    """

    user = await helpers.return_one(user_id, models.User, local.session)
    return await helpers.get_all_of_model(models.Communism, local, creator=user)


@router.get(
    "/participant/{user_id}",
    response_model=List[schemas.Communism],
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_communisms_by_participant(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return a list of all communisms where the specified user has participated in.

    A 404 error will be returned if the user ID is unknown.
    """

    user = await helpers.return_one(user_id, models.User, local.session)
    memberships = await helpers.return_all(models.CommunismUsers, local.session, user=user)
    return [membership.communism.schema for membership in memberships]


@router.post(
    "/abort/{communism_id}",
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def abort_open_communism(
        communism_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Abort an open communism (closing it without performing transactions)

    A 400 error will be returned if the communism is already closed.
    A 404 error will be returned if the communism ID is unknown.
    """

    model = await helpers.return_one(communism_id, models.Communism, local.session)

    if not model.active:
        raise BadRequest("Updating an already closed communism is not possible.", detail=str(model))

    model.active = False
    logger.debug(f"Aborting communism {model}")
    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)


@router.post(
    "/close/{communism_id}",
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def close_open_communism(
        communism_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Close an open communism (closing it with performing transactions)

    A 400 error will be returned if the communism is already closed.
    A 404 error will be returned if the communism ID is unknown.
    """

    model = await helpers.return_one(communism_id, models.Communism, local.session)
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
    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)


@router.post(
    "/setParticipants/{communism_id}",
    response_model=schemas.Communism,
    responses={k: {"model": schemas.APIError} for k in (400, 404)}
)
@versioning.versions(1)
async def set_participants_of_open_communism(
        communism_id: pydantic.NonNegativeInt,
        participants: List[schemas.CommunismUserBinding],
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Set the participants of an open communism

    A 400 error will be returned if the communism is already closed or if
    any participant is an external user without voucher or a disabled user.
    A 404 error will be returned if the communism ID or the
    user ID of any mentioned participant is unknown.
    A 409 error will be returned if the community user is part of the participants.
    """

    model = await helpers.return_one(communism_id, models.Communism, local.session)

    if not model.active:
        raise BadRequest("Updating an already closed communism is not possible.", detail=str(model))

    participants = _compress_participants(participants)
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

    return await helpers.update_model(model, local, logger, helpers.ReturnType.SCHEMA)
