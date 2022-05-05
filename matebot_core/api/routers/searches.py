"""
MateBot router module for read-only search endpoints
"""

from typing import List, Optional

import pydantic
from fastapi import Depends

from ._router import router
from ..dependency import LocalRequestData
from .. import helpers, versioning
from ...persistence import models
from ... import schemas


################
# APPLICATIONS #
################


@router.get("/applications", tags=["Searches"], response_model=List[schemas.Application])
@versioning.versions(minimal=1)
async def search_for_applications(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        name: Optional[pydantic.constr(max_length=255)] = None,
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
        id=id,
        name=name
    )


###########
# BALLOTS #
###########


@router.get("/ballots", tags=["Searches"], response_model=List[schemas.Ballot])
@versioning.versions(minimal=1)
async def search_for_ballots(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
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
        id=id
    )


###############
# CONSUMABLES #
###############


@router.get("/consumables", tags=["Searches"], response_model=List[schemas.Consumable])
@versioning.versions(minimal=1)
async def search_for_consumables(
        name: Optional[pydantic.constr(max_length=255)] = None,
        description: Optional[pydantic.constr(max_length=255)] = None,
        price: Optional[pydantic.PositiveInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all consumables that fulfill *all* constraints given as query parameters
    """

    return [
        consumable for consumable in local.config.consumables
        if (name is None or consumable.name == name)
        and (description is None or consumable.description == description)
        and (price is None or consumable.price == price)
    ]


######################
# MULTI TRANSACTIONS #
######################


@router.get("/multitransactions", tags=["Searches"], response_model=List[schemas.MultiTransaction])
@versioning.versions(1)
async def search_for_multi_transactions(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
        base_amount: Optional[pydantic.NonNegativeInt] = None,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return all multi transactions that fulfill *all* constraints given as query parameters
    """

    return helpers.search_models(
        models.MultiTransaction,
        local,
        id=id,
        base_amount=base_amount
    )


#########
# VOTES #
#########


@router.get("/votes", tags=["Searches"], response_model=List[schemas.Vote])
@versioning.versions(minimal=1)
async def search_for_votes(
        id: Optional[pydantic.NonNegativeInt] = None,  # noqa
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
        id=id,
        vote=vote,
        ballot_id=ballot_id,
        user_id=user_id
    )
