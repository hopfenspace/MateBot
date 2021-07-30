"""
Generic helper library for the core REST API
"""

import logging
from typing import List, Optional, Type

import pydantic
import sqlalchemy.exc

from .base import APIException
from .dependency import LocalRequestData
from ..persistence import models


def get_all_of_model(
        model: Type[models.Base],
        local: LocalRequestData,
        **kwargs
) -> List[pydantic.BaseModel]:
    """
    Get a list of all known objects of a given model

    This method will also take care of handling any conditional request headers
    and setting the correct ``ETag`` header (besides the others) in the response.

    :param model: class of a SQLAlchemy model
    :param local: contextual local data
    :param kwargs: dictionary of additional headers for the response
    :return: resulting list of entities
    """

    all_schemas = [obj.schema for obj in local.session.query(model).all()]
    local.entity.model_name = model.__name__
    local.entity.compare(all_schemas)
    return local.attach_headers(all_schemas, **kwargs)


def create_new_of_model(
        model: models.Base,
        local: LocalRequestData,
        logger: Optional[logging.Logger] = None,
        **kwargs
) -> pydantic.BaseModel:
    """
    Create a new model's entry in the database

    This method will also take care of handling any conditional request headers
    and setting the correct ``ETag`` header (besides the others) in the response.

    :param model: instance of a new SQLAlchemy model without any associated session
    :param local: contextual local data
    :param logger: optional logger that should be used for INFO and ERROR messages
    :param kwargs: dictionary of additional headers for the response
    :return: resulting object (as its schema's instance)
    :raises APIException: when the database operation went wrong (to report the problem)
    """

    local.entity.model_name = type(model).__name__
    local.entity.compare(None)

    if logger is not None:
        logger.info(f"Adding new model {model!r}...")

    try:
        local.session.add(model)
        local.session.commit()
    except sqlalchemy.exc.DBAPIError as exc:
        local.session.rollback()

        if logger is not None:
            details = exc.statement.replace("\n", "")
            logger.error(f"{type(exc).__name__}: {', '.join(exc.args)} @ {details!r}")

        raise APIException(
            status_code=400,
            detail=f"Problem arguments: {', '.join(exc.args)!r}",
            repeat=False,
            message=f"Database error: {type(exc).__name__!r}"
        ) from exc

    return local.attach_headers(model.schema, **kwargs)
