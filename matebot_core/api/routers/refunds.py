"""
MateBot router module for /refunds requests
"""

from typing import List

import pydantic
from fastapi import APIRouter, Depends

from ..base import MissingImplementation
from ..dependency import LocalRequestData
from ... import schemas


router = APIRouter(
    prefix="/refunds",
    tags=["Refunds"]
)


@router.get(
    "",
    response_model=List[pydantic.NonNegativeInt],
    description="Return a list of all known refund IDs in the system."
)
def get_all_known_refund_ids(local: LocalRequestData = Depends(LocalRequestData)):
    raise MissingImplementation("get_all_known_refund_ids")


@router.post(
    "",
    response_model=schemas.Refund,
    responses={404: {}},
    description="Create a new refund based on the specified data. A 404 error will be "
                "returned if the user ID of the creator of that refund is unknown."
)
def create_new_refund(
        refund: schemas.IncomingRefund,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("create_new_refund")


@router.put(
    "",
    response_model=schemas.Refund,
    responses={404: {}, 409: {}},
    tags=["Refunds"],
    description="Update an existing refund based on the specified data. A 404 error "
                "will be returned if the refund ID was not found. A 409 error will "
                "be returned if any of the following fields was changed (compared to the "
                "previous values of that refund ID): `amount`, `description`, `creator`, "
                "`active`. This prevents modifications of refund requests after their "
                "creation. A 409 error will also be returned if the operation was "
                "performed on a closed refund. This method will merely update the votes "
                "for approval or refusal of the refunding request. Use the other "
                "POST method to eventually cancel a request if necessary."
)
def update_existing_refund(
        refund: schemas.Refund,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("update_existing_refund")


@router.get(
    "/{refund_id}",
    response_model=schemas.Refund,
    responses={404: {}},
    tags=["Refunds"],
    description="Return an existing refund. A 404 error will be returned "
                "if the specified refund ID was not found."
)
def get_refund_by_id(
        refund_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_refund_by_id")


@router.get(
    "/creator/{user_id}",
    response_model=List[schemas.Refund],
    responses={404: {}},
    tags=["Refunds"],
    description="Return a list of all refunds which have been created by the user with "
                "that `user_id`. A 404 error will be returned if the user ID is unknown."
)
def get_refunds_by_creator(
        user_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("get_refunds_by_creator")


@router.post(
    "/{refund_id}/cancel",
    response_model=schemas.Refund,
    responses={404: {}, 409: {}},
    tags=["Refunds"],
    description="Cancel an existing refund operation. A 409 error will be returned if "
                "this is attempted on a closed/inactive refund operation. A 404 error "
                "will be returned if the specified `refund_id` is not known. This "
                "operation closes the refund and prevents any further changes. "
                "No transactions will be performed based on this refund anymore."
)
def cancel_existing_refund(
        refund_id: pydantic.NonNegativeInt,
        local: LocalRequestData = Depends(LocalRequestData)
):
    raise MissingImplementation("cancel_existing_refund")
