"""
Generic helper library for the core REST API
"""

import logging
from typing import Callable, List, Optional, Tuple, Type, Union

import pydantic
import sqlalchemy.orm
from fastapi.responses import Response

from .base import BadRequest, NotFound
from .dependency import LocalRequestData
from ..persistence import models
from ..misc.logger import enforce_logger
from ..misc.notifier import Callback


def add_callback(
        operation: Union[str, Callback.Operation],
        model: Union[models.Base, Tuple[Union[str, Type[models.Base]], int]],
        local: LocalRequestData
) -> None:
    """
    Add a callback operation to the background task queue

    :param operation: either a valid string or enum referencing a callback
        operation (one of `created`, `updated` or `deleted`)
    :param model: either the instance of an already created & committed SQLAlchemy model or a
        tuple of the model type and the model ID (where the type is either a class or a string)
    :param local: contextual local data
    """

    if isinstance(operation, str):
        operation = Callback.Operation(operation)
    elif not isinstance(operation, Callback.Operation):
        raise TypeError("Invalid operation type")
    callback_function = getattr(Callback, operation.value, None)
    if callback_function is None:
        raise RuntimeError("Invalid callback name doesn't match enum value")

    if isinstance(model, models.Base):
        model_type = type(model).__name__
        model_id = model.id
        if model_id is None:
            raise ValueError("Models must be committed to the database to trigger callbacks (missing ID)")
    elif isinstance(model, tuple):
        if len(model) != 2:
            raise ValueError("Invalid tuple length to specify callbacks")
        model_type, model_id = model
        if isinstance(model_type, sqlalchemy.orm.decl_api.DeclarativeMeta):
            model_type = model_type.__name__
        elif not isinstance(model_type, str):
            raise ValueError("Model type must either be a string or a valid declarative class")
    else:
        raise TypeError("Invalid model type definition for callback triggering")

    local.tasks.add_task(
        callback_function,
        str(model_type).lower(),
        int(model_id),
        local.session.query(models.Callback).all()
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
        raise NotFound(f"{model.__name__} with ID {object_id!r}")
    return obj


async def resolve_user_spec(user_spec: Union[str, int], local: LocalRequestData) -> models.User:
    """
    Resolve a user specification, which might be a user ID or a unique, confirmed alias (requiring the origin app)

    :param user_spec: either the user ID or the 'username' in an alias
        of the given application (which must be confirmed!)
    :param local: contextual local data
    :return: resulting user as SQLAlchemy model
    :raises BadRequest: when no or multiple users were found for the given user spec
    :raises NotFound: when the specified object ID returned no result
    :raises InternalServerException: when no valid application was given along a string user spec
    :raises TypeError: when the user spec is neither string nor int
    """

    if isinstance(user_spec, int):
        return await return_one(user_spec, models.User, local.session)
    if not isinstance(user_spec, str):
        raise TypeError(f"Expected int or str, found {type(user_spec)}")

    possible_aliases = search_models(
        models.Alias,
        local,
        application_id=local.origin_app.id,
        confirmed=True,
        username=user_spec
    )

    if len(possible_aliases) > 1:
        raise BadRequest(f"Multiple users were found for '{user_spec}'. Please ensure user aliases are unique.")
    elif len(possible_aliases) == 0:
        raise BadRequest(f"No users were found for '{user_spec}'. Please ensure such a user alias exists.")
    user_id = possible_aliases[0].user_id
    return await return_one(user_id, models.User, local.session)


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


async def create_new_of_model(
        model: models.Base,
        local: LocalRequestData,
        logger: Optional[logging.Logger] = None
) -> pydantic.BaseModel:
    """
    Create a new model's entry in the database (triggering callbacks)

    :param model: instance of a new SQLAlchemy model without any associated session
    :param local: contextual local data
    :param logger: optional logger that should be used for INFO and ERROR messages
    :return: resulting object (as its schema's instance)
    :raises APIException: when the database operation went wrong (to report the problem)
    """

    enforce_logger(logger).debug(f"Adding new model {model!r}...")
    local.session.add(model)
    local.session.commit()

    local.tasks.add_task(
        Callback.created,
        type(model).__name__.lower(),
        model.id,
        local.session.query(models.Callback).all()
    )

    return model.schema


async def update_model(
        model: models.Base,
        local: LocalRequestData,
        logger: Optional[logging.Logger] = None
):
    """
    Add the updated model to a database transaction and commit it (triggering callbacks)

    :param model: instance of the updated SQLAlchemy model
    :param local: contextual local data
    :param logger: optional logger that should be used for INFO and ERROR messages
    """

    enforce_logger(logger).debug(f"Updating model {model!r}...")
    local.session.add(model)
    local.session.commit()

    local.tasks.add_task(
        Callback.updated,
        type(model).__name__.lower(),
        model.id,
        local.session.query(models.Callback).all()
    )

    return model.schema


async def delete_one_of_model(
        instance_id: pydantic.NonNegativeInt,
        model: Type[models.Base],
        local: LocalRequestData,
        logger: Optional[logging.Logger] = None
):
    """
    Delete the identified instance of a model from the database (triggering callbacks)

    :param instance_id: unique identifier of the instance to be deleted
    :param model: class of the SQLAlchemy model
    :param local: contextual local data
    :param logger: optional logger that should be used for INFO and ERROR messages
    :raises NotFound: when the specified ID can't be found for the given model
    :raises Conflict: when the given schema does not conform to the current state of the object
    """

    obj = await return_one(instance_id, model, local.session)
    enforce_logger(logger).debug(f"Deleting model {obj!r}...")
    local.session.delete(obj)
    local.session.commit()

    local.tasks.add_task(
        Callback.deleted,
        type(obj).__name__.lower(),
        instance_id,
        local.session.query(models.Callback).all()
    )

    return Response(status_code=204)
