"""
MateBot router module for /votes requests
"""

import logging
from typing import List

from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from .. import helpers
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/votes",
    tags=["Votes"]
)


@router.get(
    "",
    response_model=List[schemas.Vote],
    description="Return a list of all votes in the system."
)
def get_all_votes(local: LocalRequestData = Depends(LocalRequestData)):
    return helpers.get_all_of_model(models.Vote, local)


@router.post(
    "",
    response_model=schemas.Vote,
    responses={404: {"model": schemas.APIError}, 409: {"model": schemas.APIError}},
    description="Add a new vote to some open ballot. A 404 error will be returned "
                "if either the user ID or the ballot ID was not found. A 409 error "
                "will be returned if either the ballot has already been closed or "
                "the user has already voted in the ballot -- maybe use `PUT` instead."
)
def add_new_vote(
        vote: schemas.VoteCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("add_new_vote")


@router.put(
    "",
    response_model=schemas.Vote,
    responses={
        403: {"model": schemas.APIError},
        404: {"model": schemas.APIError},
        409: {"model": schemas.APIError}
    },
    description="Update the `vote` value of an existing vote. Note that this method only "
                "accepts changes to the `vote` field. Modifying the `modified` field "
                "would lead to a 409 error. A 409 error will also be returned if the "
                "combination of `user_id` and `ballot_id` doesn't match the specified "
                "`id`. A 404 error will be returned if the vote ID is unknown. A 403 "
                "error will be returned if the ballot is restricted (forbidding changes)."
)
def change_existing_vote(
        vote: schemas.Vote,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("change_existing_vote")


@router.delete(
    "",
    status_code=201,
    responses={
        403: {"model": schemas.APIError},
        404: {"model": schemas.APIError},
        409: {"model": schemas.APIError}
    },
    description="Delete an existing vote identified by its `id`. A 409 error will be returned "
                "if the combination of `user_id` and `ballot_id` doesn't match the "
                "specified `id`. A 404 error will be returned if the vote ID is unknown. "
                "A 403 error will be returned if the ballot is restricted, i.e. votes can't "
                "be removed from the ongoing ballot as soon as it has been created."
)
def delete_existing_vote(
        vote: schemas.Vote,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("delete_existing_vote")
