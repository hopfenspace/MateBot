"""
MateBot router module for /communisms requests
"""

import logging
from typing import List, Union

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


async def _check_participants(communism: Union[schemas.Communism, schemas.CommunismCreation], local: LocalRequestData):
    participants = {
        p.user_id: await helpers.return_one(p.user_id, models.User, local.session)
        for p in communism.participants
    }
    if [
        k for k in participants
        if not participants[k].active or (participants[k].external and participants[k].voucher is None)
    ]:
        raise BadRequest("Disabled users or externals without voucher can't participate in communisms.")
    if len(communism.participants) != len(participants):
        raise Conflict(
            message="At least one user was mentioned more than once in the communism member list",
            detail=str(communism.participants)
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
    responses={400: {"model": schemas.APIError}, 404: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def create_new_communism(
        communism: schemas.CommunismCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Create a new communism based on the specified data.

    A 400 error will be returned if any participant was mentioned
    more than one time. A 404 error will be returned if the user ID
    of the `creator` or any mentioned participant is unknown.
    """

    creator = await helpers.return_one(communism.creator_id, models.User, local.session)
    if not creator.active:
        raise BadRequest("A disabled user can't create communisms.")
    if creator.external and creator.voucher_id is None:
        raise BadRequest("You can't create communisms without having a voucher user.")

    await _check_participants(communism, local)

    model = models.Communism(
        amount=communism.amount,
        description=communism.description,
        creator=creator,
        active=communism.active,
        participants=[]
    )

    async def hook(*_):
        local.session.add_all([
            models.CommunismUsers(communism_id=model.id, user_id=p.user_id, quantity=p.quantity)
            for p in communism.participants
        ])
        local.session.commit()

    return await helpers.create_new_of_model(model, local, logger, hook_func=hook)




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
