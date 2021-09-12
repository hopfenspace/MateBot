"""
MateBot router module for /communisms requests
"""

import logging
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import APIException, Conflict, MissingImplementation
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/communisms",
    tags=["Communisms"]
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

    creator = await helpers.return_one(communism.creator, models.User, local.session)
    if len(communism.participants) != len({
        p.user: await helpers.return_one(p.user, models.User, local.session)
        for p in communism.participants
    }):
        raise APIException(
            status_code=400,
            message="At least one user was mentioned more than once in the communism member list",
            detail=str(communism.participants)
        )

    model = models.Communism(
        amount=communism.amount,
        description=communism.description,
        creator=creator,
        active=communism.active,
        externals=communism.externals,
        participants=[]
    )

    async def hook(*args):
        local.session.add_all([
            models.CommunismUsers(communism_id=model.id, user_id=p.user, quantity=p.quantity)
            for p in communism.participants
        ])
        local.session.commit()

    return await helpers.create_new_of_model(model, local, logger, hook_func=hook)


@router.patch(
    "",
    response_model=schemas.Communism,
    responses={
        400: {"model": schemas.APIError},
        404: {"model": schemas.APIError},
        409: {"model": schemas.APIError}
    }
)
@versioning.versions(minimal=1)
async def update_existing_communism(
        communism: schemas.CommunismPatch,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Change certain pieces of mutable information about an already existing communism.

    The fields `externals` and `participants` will be used as-is to overwrite
    the internal state of the communism (which will be returned afterwards).

    A 400 error will be returned if any participant was mentioned more
    than one time. A 404 error will be returned if the communism ID was
    not found or if the user ID of any mentioned participant is unknown.
    A 409 error will be returned if a closed communism was altered.
    """

    model = await helpers.return_one(communism.id, models.Communism, local.session)
    schema = model.schema

    if communism.participants is not None and len(communism.participants) != len({
        p.user: await helpers.return_one(p.user, models.User, local.session)
        for p in communism.participants
    }):
        raise APIException(
            status_code=400,
            message="At least one user was mentioned more than once in the communism member list",
            detail=str(communism.participants)
        )

    if not model.active:
        raise Conflict("Patching an already closed communism is illegal", detail=str(communism))

    if communism.externals is not None:
        model.externals = communism.externals

    if communism.participants is not None:
        for p in model.participants:
            local.session.delete(p)
        model.participants = [
            models.CommunismUsers(communism_id=model.id, user_id=p.user, quantity=p.quantity)
            for p in communism.participants
        ]

    if communism.close is not None and communism.close:
        raise MissingImplementation("update_existing_communism_patch_close_communism")

    return await helpers.update_model(
        model,
        local,
        logger,
        require_conditional_header_compared_to_schema=schema
    )


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
