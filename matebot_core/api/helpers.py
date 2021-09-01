"""
Generic helper library for the core REST API
"""

import sys
import logging
from typing import Any, Callable, List, Optional, Type

import pydantic
import sqlalchemy.exc
import sqlalchemy.orm

from .base import APIException, Conflict, NotFound
from .dependency import LocalRequestData
from ..persistence import models


async def _handle_db_exception(
        session: sqlalchemy.orm.Session,
        exc: sqlalchemy.exc.DBAPIError,
        logger: logging.Logger,
        repeat: bool = False
) -> APIException:
    """
    Handle DBAPIError exceptions by creating a ``APIError`` instance out of it

    :param session: sqlalchemy session instance which will be rolled back
    :param exc: instance of the currently handled exception
    :param logger: logger to be used for error reporting and traceback printing
    :param repeat: value directly passed trough the ``APIError`` constructor
    :return: instance of APIException, which should be raised in a ``raise from`` clause
    :raises RuntimeError: when the exception doesn't equal the one found in ``sys.exc_info()``
    :raises TypeError: when an existing exception is no instance of class ``DBAPIError``
    """

    if sys.exc_info()[1] is None or sys.exc_info()[1] != exc:
        raise RuntimeError(f"Called {_handle_db_exception!r} in wrong exception handler!")
    if not isinstance(exc, sqlalchemy.exc.DBAPIError):
        raise TypeError(f"Expected instance of DBAPIError, found {type(exc)}") from exc

    session.rollback()

    details = exc.statement.replace("\n", "")
    logger.error(f"{type(exc).__name__}: {', '.join(exc.args)} @ {details!r}", exc_info=exc)

    return APIException(
        status_code=400,
        detail=f"Problem arguments: {', '.join(exc.args)!r}",
        repeat=repeat,
        message=f"Database error: {type(exc).__name__!r}"
    )


async def return_one(
        object_id: int,
        model: Type[models.Base],
        session: sqlalchemy.orm.Session
) -> models.Base:
    """
    Return the object of a given model that's identified by its object ID

    :param object_id: internal ID (primary key in the database) of the model
    :param model: class of a SQLAlchemy model
    :param session: database session which should be used to perform the query
    :return: resulting entity as SQLAlchemy model
    :raises NotFound: when the specified object ID returned no result
    """

    obj = session.get(model, object_id)
    if obj is None:
        raise NotFound(f"{model.__name__} ID {object_id!r}")
    return obj


async def return_unique(
        model: Type[models.Base],
        session: sqlalchemy.orm.Session,
        **kwargs
) -> models.Base:
    """
    Return the unique object of a given model, filtered by the keyword arguments

    :param model: class of a SQLAlchemy model
    :param session: database session which should be used to perform the query
    :param kwargs: mandatory filter arguments for the database query
    :return: resulting single, unique entity
    :raises NotFound: when the query returned no result or more than one result
    """

    all_objects = session.query(model).filter_by(**kwargs).all()
    if len(all_objects) == 1:
        return all_objects[0]
    raise NotFound(
        f"Unique {model.__name__} instance",
        detail=f"kwargs={kwargs!s}, hits={len(all_objects)}"
    )


async def get_one_of_model(
        object_id: int,
        model: Type[models.Base],
        local: LocalRequestData,
        headers: Optional[dict] = None
) -> pydantic.BaseModel:
    """
    Get the object of a given model that's identified by its object ID

    This method will also take care of handling any conditional request headers
    and setting the correct ``ETag`` header (besides the others) in the response.

    :param object_id: internal ID (primary key in the database) of the model
    :param model: class of a SQLAlchemy model
    :param local: contextual local data
    :param headers: additional headers for the response
    :return: resulting entity as pydantic schema instance
    :raises NotFound: when the specified object ID returned no result
    """

    obj = await return_one(object_id, model, local.session)
    schema = obj.schema
    local.entity.model_name = model.__name__
    local.entity.compare(schema)
    if headers and isinstance(headers, dict):
        return local.attach_headers(schema, **headers)
    return local.attach_headers(schema)


async def get_all_of_model(
        model: Type[models.Base],
        local: LocalRequestData,
        headers: Optional[dict] = None,
        **kwargs
) -> List[pydantic.BaseModel]:
    """
    Get a list of all known objects of a given model

    This method will also take care of handling any conditional request headers
    and setting the correct ``ETag`` header (besides the others) in the response.

    :param model: class of a SQLAlchemy model
    :param local: contextual local data
    :param headers: additional headers for the response
    :param kwargs: additional filter arguments for the database query
    :return: resulting list of entities
    """

    all_schemas = [obj.schema for obj in local.session.query(model).filter_by(**kwargs).all()]
    local.entity.model_name = model.__name__
    local.entity.compare(all_schemas)
    if headers and isinstance(headers, dict):
        return local.attach_headers(all_schemas, **headers)
    return local.attach_headers(all_schemas)


async def create_new_of_model(
        model: models.Base,
        local: LocalRequestData,
        logger: Optional[logging.Logger] = None,
        location_format: Optional[str] = None,
        content_location: bool = False,
        more_models: Optional[List[models.Base]] = None,
        **kwargs
) -> pydantic.BaseModel:
    """
    Create a new model's entry in the database

    This method will also take care of handling any conditional request headers
    and setting the correct ``ETag`` header (besides the others) in the response.
    The response will usually be delivered with a 201 (Created) status code, which
    should be declared by the calling function. The ``Location`` header field will
    be set according to the given format string in the :param:`location_format`.
    Use one unnamed placeholder which should be filled with the ID of the newly
    created resource to get a working ``Location`` reference to the new object.
    The boolean flag ``content_location`` defines whether a ``Content-Location``
    header should be set, too. See RFC 7231, section 3.1.4.2, for more information.

    :param model: instance of a new SQLAlchemy model without any associated session
    :param local: contextual local data
    :param logger: optional logger that should be used for INFO and ERROR messages
    :param location_format: optional format string to produce the ``Location`` header
    :param content_location: switch to enable adding the ``Content-Location`` header,
        too (only applicable if the ``Location`` header has been set before, not alone)
    :param more_models: list of additional models to be committed in the same transaction
    :param kwargs: additional headers for the response
    :return: resulting object (as its schema's instance)
    :raises APIException: when the database operation went wrong (to report the problem)
    """

    if logger is None:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"No logger specified for function call with args: {model, more_models}"
        )

    local.entity.model_name = type(model).__name__
    local.entity.compare(None)

    logger.info(f"Adding new model {model!r}...")
    if more_models is not None:
        for m in more_models:
            logger.debug(f"Additional model: {m!r}")

    try:
        local.session.add(model)
        if more_models is not None:
            local.session.add_all(more_models)
        local.session.commit()

    except sqlalchemy.exc.DBAPIError as exc:
        raise await _handle_db_exception(local.session, exc, logger) from exc

    headers = kwargs
    if location_format is not None:
        headers["Location"] = location_format.format(model.id)
        if content_location:
            headers["Content-Location"] = headers["Location"]
    return local.attach_headers(model.schema, **headers)


async def delete_one_of_model(
        instance_id: pydantic.NonNegativeInt,
        model: Type[models.Base],
        local: LocalRequestData,
        require_conditional_header: bool = True,
        schema: Optional[pydantic.BaseModel] = None,
        logger: Optional[logging.Logger] = None,
        hook_func: Optional[Callable[[models.Base, LocalRequestData, logging.Logger], Any]] = None
):
    """
    Delete the identified instance of a model from the database

    :param instance_id: unique identifier of the instance to be deleted
    :param model: class of the SQLAlchemy model
    :param local: contextual local data
    :param require_conditional_header: force the user agent to provide a valid conditional request
        header before proceeding with the action, otherwise abort further operation
    :param schema: optional supplied schema of the request to validate the client's state
    :param logger: optional logger that should be used for INFO and ERROR messages
    :param hook_func: optional callable which will be called after all previous checks
        on the request, the instance, the model and the schema have succeeded (this
        callable should not return anything, but may raise appropriate HTTP exceptions);
        it's recommended that this function uses local values from the definition namespace
    :raises NotFound: when the specified ID can't be found for the given model
    :raises Conflict: when the given schema does not conform to the current state of the object
    :raises PreconditionFailed: if no valid conditional request header has been set
    """

    if logger is None:
        logger = logging.getLogger(__name__)
        logger.warning(
            f"No logger specified for function call with args: {instance_id, model, schema}"
        )

    cls_name = type(schema).__name__
    obj = await return_one(instance_id, model, local.session)

    if require_conditional_header:
        local.entity.model_name = models.User.__name__
        local.entity.compare(obj.schema)

    if schema is not None and obj.schema != schema:
        raise Conflict(
            f"Invalid state of the {cls_name}. Query the {cls_name} to update.",
            f"current={obj.schema!r}, requested={schema!r}"
        )

    if hook_func is not None and isinstance(hook_func, Callable):
        hook_func(obj, local, logger)

    try:
        local.session.delete(obj)
        local.session.commit()

    except sqlalchemy.exc.DBAPIError as exc:
        raise await _handle_db_exception(local.session, exc, logger) from exc
