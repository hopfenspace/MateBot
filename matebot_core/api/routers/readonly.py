"""
MateBot router module for various read-only endpoints
"""

import datetime
from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...schemas import config
from ...persistence import models
from ... import schemas, __version__


router = APIRouter(tags=["Readonly"])


################
# APPLICATIONS #
################


@router.get(
    "/applications",
    response_model=List[schemas.Application]
)
@versioning.versions(minimal=1)
async def get_all_applications(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known applications
    """

    return await helpers.get_all_of_model(models.Application, local)


@router.get(
    "/applications/{application_id}",
    response_model=schemas.Application,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_application_by_id(
        application_id: int,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the application model specified by its application ID

    A 404 error will be returned in case the ID is not found.
    """

    return await helpers.get_one_of_model(application_id, models.Application, local)


###########
# BALLOTS #
###########


@router.get(
    "/ballots",
    response_model=List[schemas.Ballot]
)
@versioning.versions(minimal=1)
async def get_all_ballots(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known ballots
    """

    return await helpers.get_all_of_model(models.Ballot, local)


@router.get(
    "/ballots/{ballot_id}",
    response_model=schemas.Ballot,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_ballot_by_id(
        ballot_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return details about a specific ballot identified by its `ballot_id`

    A 404 error will be returned if that ID is unknown.
    """

    return await helpers.get_one_of_model(ballot_id, models.Ballot, local)


###############
# CONSUMABLES #
###############


@router.get(
    "/consumables",
    response_model=List[schemas.Consumable]
)
@versioning.versions(minimal=1)
async def get_all_consumables(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all current consumables.
    """

    return await helpers.get_all_of_model(models.Consumable, local)


#########################
# GENERAL FUNCTIONALITY #
#########################


@router.get("/settings", response_model=config.GeneralConfig)
@versioning.versions(minimal=1)
async def get_settings(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return the important MateBot core settings which directly affect the handling of requests
    """

    return local.config.general


@router.get("/status", response_model=schemas.Status)
@versioning.versions(1)
async def get_status(_: LocalRequestData = Depends(LocalRequestData)):
    """
    Return some information about the current status of the server, the database and whatsoever
    """

    project_version_list = __version__.split(".") + [0, 0]
    project_version = schemas.VersionInfo(
        major=project_version_list[0],
        minor=project_version_list[1],
        micro=project_version_list[2]
    )

    return schemas.Status(
        api_version=1,
        project_version=project_version,
        localtime=datetime.datetime.now(),
        timestamp=datetime.datetime.now().timestamp()
    )


#########
# VOTES #
#########


@router.get(
    "/votes",
    response_model=List[schemas.Vote]
)
@versioning.versions(minimal=1)
async def get_all_votes(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known votes
    """

    return await helpers.get_all_of_model(models.Vote, local)


@router.get(
    "/votes/{vote_id}",
    response_model=schemas.Vote,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_vote_by_id(
        vote_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return details about a specific vote identified by its `vote_id`

    A 404 error will be returned if that ID is unknown.
    """

    return await helpers.get_one_of_model(vote_id, models.Vote, local)
