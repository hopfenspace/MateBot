"""
MateBot router module for /applications requests
"""

import logging
import secrets
from typing import List

from fastapi import APIRouter, Depends

from ..dependency import LocalRequestData
from .. import auth, helpers, versioning
from ...persistence import models
from ... import schemas


logger = logging.getLogger(__name__)

router = APIRouter(prefix="/applications", tags=["Applications"])


@router.get(
    "",
    response_model=List[schemas.Application]
)
@versioning.versions(minimal=1)
async def get_all_applications(local: LocalRequestData = Depends(LocalRequestData)):
    """
    Return a list of all known applications.
    """

    return await helpers.get_all_of_model(models.Application, local)


@router.post(
    "",
    status_code=201,
    response_model=schemas.Application,
    responses={409: {"model": schemas.APIError}}
)
@versioning.versions(minimal=1)
async def add_new_application(
        application: schemas.ApplicationCreation,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Add a new "empty" application and create a new ID for it.

    This will also create a new alias for the community user,
    taking the `community_user_name` as the app's user ID. This
    special user will be used to e.g. pay refunds to individual users.

    A 409 error will be returned if the application name is already taken.
    """

    community = await helpers.return_unique(models.User, local.session, special=True)
    await helpers.expect_none(models.Application, local.session, name=application.name)
    salt = secrets.token_urlsafe(16)
    passwd = models.Password(salt=salt, passwd=auth.hash_password(application.password, salt))
    app = models.Application(name=application.name, password=passwd)

    alias = models.UserAlias(
        user_id=community.id,
        app_user_id=application.community_user_name,
        app=app
    )

    def hook(*_):
        app.community_user_alias = alias
        local.session.add(app)
        local.session.commit()

    return await helpers.create_new_of_model(
        app,
        local,
        logger,
        more_models=[alias],
        hook_func=hook
    )


@router.get(
    "/{application_id}",
    response_model=schemas.Application,
    responses={404: {"model": schemas.APIError}}
)
@versioning.versions(1)
async def get_application_by_id(
        application_id: int,
        local: LocalRequestData = Depends(LocalRequestData)
):
    """
    Return the application model specified by its application ID.

    A 404 error will be returned in case the ID is not found.
    """

    return await helpers.get_one_of_model(application_id, models.Application, local)
