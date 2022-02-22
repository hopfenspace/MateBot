"""
Generic helper library for the core REST API
"""

import sys
import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type

import pydantic
import sqlalchemy.exc
import sqlalchemy.orm
from fastapi.responses import Response

from .base import APIException, Conflict, ForbiddenChange, InternalServerException, NotFound, Operations, ReturnType
from .dependency import LocalRequestData
from ..persistence import models
from ..misc.logger import enforce_logger
from ..misc.notifier import Callback
from ..schemas.bases import BaseModel


_CallbackType = Callable[[str, str, logging.Logger, sqlalchemy.orm.Session], None]
HookType = Callable[[models.Base, LocalRequestData, logging.Logger], Any]


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
    logger = enforce_logger(logger)
    logger.error(f"{type(exc).__name__}: {', '.join(exc.args)} @ {details!r}", exc_info=exc)

    return APIException(
        status_code=400,
        detail=f"Problem arguments: {', '.join(exc.args)!r}",
        repeat=repeat,
        message=f"Database error: {type(exc).__name__!r}"
    )


async def _commit(
        session: sqlalchemy.orm.Session,
        *objects: models.Base,
        logger: Optional[logging.Logger] = None
) -> bool:
    """
    Add all specified objects to the database session and commit it

    :param session: database session which should be used for committing the data
    :param objects: collection of models that should be added to the database transaction
    :param logger: optional logger (which will be enforced when omitted)
    :return: True in case everything went smoothly
    :raises APIException: in case something went wrong
    """

    try:
        session.add_all(objects)
        session.commit()
    except sqlalchemy.exc.DBAPIError as exc:
        raise await _handle_db_exception(session, exc, enforce_logger(logger)) from exc
    return True


async def _call_hook(
        hook_func: HookType,
        model: models.Base,
        local: LocalRequestData,
        logger: logging.Logger
) -> Any:
    """
    Call the specified hook function with the supplied three arguments
    """

    if hook_func is not None and isinstance(hook_func, Callable):
        try:
            if asyncio.iscoroutinefunction(hook_func):
                logger.debug(f"Calling hook coroutine {hook_func} with {model} ...")
                return await hook_func(model, local, logger)
            else:
                logger.debug(f"Calling hook function {hook_func} with {model} ...")
                return hook_func(model, local, logger)
        except sqlalchemy.exc.DBAPIError as exc:
            raise await _handle_db_exception(local.session, exc, logger) from exc
        except TypeError as exc:
            logger.exception(f"Broken hook function {hook_func} raised: {exc} (TypeError)")
            raise
        except APIException as exc:
            logger.exception(f"APIException: {exc!r} during hook {hook_func}")
            raise
    elif hook_func is not None:
        raise TypeError(f"{hook_func!r} object is not callable")


def _return_expected(
        returns: ReturnType,
        model: models.Base,
        local: LocalRequestData,
        headers: Optional[Dict[str, Any]] = None
) -> Optional[pydantic.BaseModel]:
    """
    Select the appropriate returned value based on the given return type enum
    """

    if headers:
        for k in headers:
            local.response.headers.append(k, headers[k])
    return {
        ReturnType.NONE: None,
        ReturnType.MODEL: model,
        ReturnType.SCHEMA: model.schema
    }[returns]


async def expect_none(model: Type[models.Base], session: sqlalchemy.orm.Session, **kwargs) -> None:
    """
    Expect to find no values in the dataset that match the keyword args for that model

    :param model: class of a SQLAlchemy model
    :param session: database session which should be used to perform the query
    :param kwargs: mandatory filter arguments for the database query
    :return: None
    :raises Conflict: when at least one entity was returned by the database query
    """

    matches = session.query(model).filter_by(**kwargs).all()
    if len(matches) > 0:
        raise Conflict(
            f"A model {model.__name__!r} already exists with that specs.",
            f"{', '.join(f'{k}={kwargs[k]!r}' for k in kwargs)}"
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


async def return_all(
        model: Type[models.Base],
        session: sqlalchemy.orm.Session,
        **kwargs
) -> List[models.Base]:
    """
    Return all objects of a given model that's identified by its object ID

    :param model: class of a SQLAlchemy model
    :param session: database session which should be used to perform the query
    :param kwargs: additional filter arguments for the database query
    :return: resulting list of entities
    """

    return session.query(model).filter_by(**kwargs).all()


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

    :param object_id: internal ID (primary key in the database) of the model
    :param model: class of a SQLAlchemy model
    :param local: contextual local data
    :param headers: additional headers for the response
    :return: resulting entity as pydantic schema instance
    :raises NotFound: when the specified object ID returned no result
    """

    obj = await return_one(object_id, model, local.session)
    if headers:
        for k in headers:
            local.response.headers.append(k, headers[k])
    return obj.schema


async def get_all_of_model(
        model: Type[models.Base],
        local: LocalRequestData,
        headers: Optional[dict] = None,
        **kwargs
) -> List[pydantic.BaseModel]:
    """
    Get a list of all known objects of a given model

    :param model: class of a SQLAlchemy model
    :param local: contextual local data
    :param headers: additional headers for the response
    :param kwargs: additional filter arguments for the database query
    :return: resulting list of entities
    """

    all_schemas = [obj.schema for obj in await return_all(model, local.session, **kwargs)]
    if headers:
        for k in headers:
            local.response.headers.append(k, headers[k])
    return all_schemas


def search_models(
        model: Type[models.Base],
        local: LocalRequestData,
        specialized_item_filter: Callable[[models.Base], bool] = None,
        **kwargs
) -> List[pydantic.BaseModel]:
    """
    Return the schemas of all user models that equal all kwargs and pass the special filter function

    :param model: class of a SQLAlchemy model
    :param local: contextual local data
    :param specialized_item_filter: callable function to filter the list of models
        explicitly with some specialized metrics (e.g. custom fields or relations)
    :param kwargs: dict of extra attribute checks on the model (empty values in the
        dict are ignored and won't be treated as check for ``None`` in the model)
    :return: list of schemas of all models that equal all kwargs and passed the filter function
    """

    query = local.session.query(model)
    for k in kwargs:
        if kwargs[k] is not None:
            query = query.filter_by(**{k: kwargs[k]})
    return [obj.schema for obj in query.all() if specialized_item_filter is None or specialized_item_filter(obj)]


# async def _handle_data_changes(
#         local: LocalRequestData,
#         operation: Operations,
#         returns: ReturnType,
#         model: Optional[models.Base] = None,
#         model_type: Optional[Type[models.Base]] = None,
#         model_id: Optional[int] = None,
#         more_models: Optional[List[models.Base]] = None,
#         logger: Optional[logging.Logger] = None,
#         location_format: Optional[str] = None,
#         content_location: bool = False,
#         trigger_callback: bool = False,
#         callback_operation: Optional[_CallbackType] = None,
#         hook_before: Optional[HookType] = None,
#         hook_after: Optional[HookType] = None,
#         extra_headers: Optional[Dict[str, Any]] = None,
# ) -> Optional[pydantic.BaseModel]:
#
#     # Make sure that all required variables are set & checked properly
#     if model is None:
#         if model_type is None or model_id is None:
#             raise InternalServerException("ValueError", "Missing model or model type with ID")
#         model = await return_one(model_id, model_type, local.session)
#     if model_type is None:
#         model_type = type(model)
#     if model_id is not None and model_id != model.id:
#         raise InternalServerException("ValueError", f"Model {model} doesn't match ID {model_id}")
#     if not isinstance(model, model_type):
#         raise InternalServerException("TypeError", f"Model {model} doesn't match {model_type}")
#     if not isinstance(operation, Operations):
#         raise InternalServerException("TypeError", f"{operation} is no {Operations} object")
#     if not isinstance(local, LocalRequestData):
#         raise InternalServerException("TypeError", f"{local} is no {LocalRequestData} object")
#
#     # Enforce to have a logger
#     logger = enforce_logger(logger)
#
#     # Execute the 'before' hook function or coroutine
#     await _call_hook(hook_before, model, local, logger)
#
#     # Add the model(s) to the database transaction and commit it
#     logger.info(f"{operation.value} models: {', '.join(map(repr, [model] + more_models))}...")
#     await _commit(local.session, model, *more_models or [], logger=logger)
#
#     # Execute the 'after' hook function or coroutine
#     await _call_hook(hook_after, model, local, logger)
#
#     # Add the callback operation to the list of background tasks to execute after the request
#     if trigger_callback and isinstance(callback_operation, Callable):
#         local.tasks.add_task(
#             callback_operation,
#             model_type.__name__.lower(),
#             model_id,
#             await return_all(models.Callback, local.session)
#         )
#
#     # Add the specified headers to the resulting response (even if they are omitted)
#     headers = extra_headers.copy()
#     if location_format is not None:
#         headers["Location"] = location_format.format(model.id)
#         if content_location:
#             headers["Content-Location"] = headers["Location"]
#     return _return_expected(returns, model, local, headers)


async def create_new_of_model(
        model: models.Base,
        local: LocalRequestData,
        logger: Optional[logging.Logger] = None,
        location_format: Optional[str] = None,
        content_location: bool = False,
        more_models: Optional[List[models.Base]] = None,
        hook_func: Optional[Callable[[models.Base, LocalRequestData, logging.Logger], Any]] = None,
        **kwargs
) -> pydantic.BaseModel:
    """
    Create a new model's entry in the database (triggering callbacks)

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
    :param hook_func: optional callable which will be called after the model(s) has/have
        been added and committed successfully but right before the triggers get activated;
        it's recommended that this function uses local values from the definition namespace
        (changing the model and committing data is possible in the hook function, too)
    :param kwargs: additional headers for the response
    :return: resulting object (as its schema's instance)
    :raises APIException: when the database operation went wrong (to report the problem)
    """

    logger = enforce_logger(logger)

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

    if hook_func is not None and isinstance(hook_func, Callable):
        try:
            if asyncio.iscoroutinefunction(hook_func):
                await hook_func(model, local, logger)
            else:
                hook_func(model, local, logger)
        except sqlalchemy.exc.DBAPIError as exc:
            raise await _handle_db_exception(local.session, exc, logger) from exc

    local.tasks.add_task(
        Callback.created,
        type(model).__name__.lower(),
        model.id,
        await return_all(models.Callback, local.session)
    )
    headers = kwargs
    if location_format is not None:
        headers["Location"] = location_format.format(model.id)
        if content_location:
            headers["Content-Location"] = headers["Location"]
    if headers:
        for k in headers:
            local.response.headers.append(k, headers[k])
    return model.schema


async def update_model(
        model: models.Base,
        local: LocalRequestData,
        logger: Optional[logging.Logger] = None,
        returns: ReturnType = ReturnType.NONE,
):
    """
    Add the updated model to a database transaction and commit it (triggering callbacks)

    :param model: instance of the updated SQLAlchemy model
    :param local: contextual local data
    :param logger: optional logger that should be used for INFO and ERROR messages
    :param returns: determine the return value and its annotations (of this function)
    """

    logger = enforce_logger(logger)

    logger.info(f"Updating model {model!r}...")
    await _commit(local.session, model, logger=logger)

    local.tasks.add_task(
        Callback.updated,
        type(model).__name__.lower(),
        model.id,
        await return_all(models.Callback, local.session)
    )

    return _return_expected(returns, model, local, {})


async def delete_one_of_model(
        instance_id: pydantic.NonNegativeInt,
        model: Type[models.Base],
        local: LocalRequestData,
        schema: Optional[pydantic.BaseModel] = None,
        logger: Optional[logging.Logger] = None,
        hook_func: Optional[HookType] = None
):
    """
    Delete the identified instance of a model from the database (triggering callbacks)

    :param instance_id: unique identifier of the instance to be deleted
    :param model: class of the SQLAlchemy model
    :param local: contextual local data
    :param schema: optional supplied schema of the request to validate the client's state
    :param logger: optional logger that should be used for INFO and ERROR messages
    :param hook_func: optional callable which will be called after all previous checks
        on the request, the instance, the model and the schema have succeeded (this
        callable should not return anything, but may raise appropriate HTTP exceptions);
        it's recommended that this function uses local values from the definition namespace
    :raises NotFound: when the specified ID can't be found for the given model
    :raises Conflict: when the given schema does not conform to the current state of the object
    """

    logger = enforce_logger(logger)
    cls_name = model.__name__
    obj = await return_one(instance_id, model, local.session)

    logger.info(f"Deleting model {obj!r}...")
    if schema is not None and obj.schema != schema:
        raise Conflict(
            f"Invalid state of the {cls_name}. Query the {cls_name} to update.",
            f"current={obj.schema!r}, requested={schema!r}"
        )

    await _call_hook(hook_func, obj, local, logger)
    logger.debug("Checks passed, deleting...")
    try:
        local.session.delete(obj)
        local.session.commit()
    except sqlalchemy.exc.DBAPIError as exc:
        raise await _handle_db_exception(local.session, exc, logger) from exc

    local.tasks.add_task(
        Callback.deleted,
        cls_name.lower(),
        instance_id,
        await return_all(models.Callback, local.session)
    )

    return Response(status_code=204)


def restrict_updates(remote_schema: BaseModel, db_schema: BaseModel) -> bool:
    """
    Compare a remote schema with the local state's schema to enforce unmodified fields

    :param remote_schema: incoming schema attached to a PUT request to be validated
    :param db_schema: schema of the local database model prior to modification
    :raises ForbiddenChange: in case the remote and local state of a "forbidden" field differs
    :raises InternalServerException: in case the schema types don't match correctly
    :return: True
    """

    if not isinstance(remote_schema, type(db_schema)):
        raise InternalServerException("Schema types don't match", f"{type(remote_schema)}!={type(db_schema)}")
    for k in db_schema.__fields__.keys():
        if not hasattr(remote_schema, k):
            raise InternalServerException("Invalid schema type", str(remote_schema))
        if k not in db_schema.__allowed_updates__ and getattr(remote_schema, k) != getattr(db_schema, k):
            raise ForbiddenChange(f"{type(db_schema).__name__}.{k}")
    return True
