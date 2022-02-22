"""
MateBot router module for various read-only endpoints
"""

import datetime
from typing import List, Optional

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
async def search_for_applications(
        application_id: Optional[pydantic.NonNegativeInt] = None,
        application_name: Optional[pydantic.constr(max_length=255)] = None,
        callback_id: Optional[pydantic.NonNegativeInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all applications that fulfill *all* constraints given as query parameters
    """

    def extended_filter(a: models.Application) -> bool:
        return callback_id is None or callback_id in [c.id for c in a.callbacks]

    return helpers.search_models(
        models.Application,
        local,
        specialized_item_filter=extended_filter,
        id=application_id,
        name=application_name
    )


###########
# BALLOTS #
###########


@router.get(
    "/ballots",
    response_model=List[schemas.Ballot]
)
@versioning.versions(minimal=1)
async def search_for_ballots(
        ballot_id: Optional[pydantic.NonNegativeInt] = None,
        vote_id: Optional[pydantic.NonNegativeInt] = None,
        ballot_for_poll: Optional[bool] = None,
        ballot_for_refund: Optional[bool] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all ballots that fulfill *all* constraints given as query parameters
    """

    def extended_filter(b: models.Ballot) -> bool:
        if vote_id is not None and vote_id not in [v.id for v in b.votes]:
            return False
        if ballot_for_poll is not None and bool(b.polls) != ballot_for_poll:
            return False
        if ballot_for_refund is not None and bool(b.refunds) != ballot_for_refund:
            return False
        return True

    return helpers.search_models(
        models.Ballot,
        local,
        specialized_item_filter=extended_filter,
        id=ballot_id
    )


###############
# CONSUMABLES #
###############


@router.get(
    "/consumables",
    response_model=List[schemas.Consumable]
)
@versioning.versions(minimal=1)
async def search_for_consumables(
        consumable_id: Optional[pydantic.NonNegativeInt] = None,
        consumable_name: Optional[pydantic.NonNegativeInt] = None,
        consumable_description: Optional[pydantic.NonNegativeInt] = None,
        consumable_price: Optional[pydantic.PositiveInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all ballots that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.Consumable,
        local,
        id=consumable_id,
        name=consumable_name,
        description=consumable_description,
        price=consumable_price
    )


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
async def search_for_votes(
        vote_id: Optional[pydantic.NonNegativeInt] = None,
        vote: Optional[bool] = None,
        ballot_id: Optional[pydantic.NonNegativeInt] = None,
        user_id: Optional[pydantic.NonNegativeInt] = None,
        vote_for_poll: Optional[bool] = None,
        vote_for_refund: Optional[bool] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all votes that fulfill *all* constraints given as query parameters
    """

    def extended_filter(v: models.Vote) -> bool:
        if vote_for_poll is not None and bool(v.ballot.polls) != vote_for_poll:
            return False
        if vote_for_refund is not None and bool(v.ballot.refunds) != vote_for_refund:
            return False
        return True

    return helpers.search_models(
        models.Vote,
        local,
        specialized_item_filter=extended_filter,
        id=vote_id,
        vote=vote,
        ballot_id=ballot_id,
        user_id=user_id
    )
