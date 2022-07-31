"""
Generic helper library for the core REST API
"""

import logging
from typing import Callable, List, Optional, Type, Union

import pydantic
import sqlalchemy
import sqlalchemy.orm
from fastapi.responses import Response

from .base import BadRequest, Conflict, NotFound
from .dependency import LocalRequestData
from ..persistence import models
from ..misc.logger import enforce_logger


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

    possible_aliases = local.session.query(models.Alias).filter_by(
        application_id=local.origin_app.id,
        confirmed=True,
        username=user_spec
    ).all()

    if len(possible_aliases) > 1:
        raise BadRequest(f"Multiple users were found for '{user_spec}'. Please ensure user aliases are unique.")
    elif len(possible_aliases) == 0:
        raise BadRequest(f"No users were found for '{user_spec}'. Please ensure such a user alias exists.")
    alias = possible_aliases[0]
    if not isinstance(alias, models.Alias):
        raise TypeError(f"Expected Alias model but got {type(alias)}")
    user_id = alias.user_id
    return await return_one(user_id, models.User, local.session)


def search_models(
        model: Type[models.Base],
        local: LocalRequestData,
        specialized_item_filter: Callable[[models.Base], bool] = None,
        limit: Optional[pydantic.NonNegativeInt] = None,
        page: Optional[pydantic.NonNegativeInt] = None,
        descending: Optional[bool] = False,
        **kwargs
) -> List[pydantic.BaseModel]:
    """
    Return the schemas of all user models that equal all kwargs and pass the special filter function

    :param model: class of a SQLAlchemy model
    :param local: contextual local data
    :param specialized_item_filter: callable function to filter the list of models
        explicitly with some specialized metrics (e.g. custom fields or relations)
    :param limit: limit the number of total results
    :param page: select a page of results, based on the page size of `limit`; if no
        limit is given, the page will be ignored due to its missing size specification
    :param descending: reverse the order of results received from the database (the
        item filter will process the reversed results, which however shouldn't matter)
    :param kwargs: dict of extra attribute checks on the model (empty values in the
        dict are ignored and won't be treated as check for ``None`` in the model)
    :return: list of schemas of all models that equal all kwargs and passed the filter function
    """

    query = local.session.query(model)
    for k in kwargs:
        if kwargs[k] is not None:
            query = query.filter_by(**{k: kwargs[k]})
    if descending:
        query = query.order_by(sqlalchemy.desc(model.id))
    results = [obj.schema for obj in query.all() if specialized_item_filter is None or specialized_item_filter(obj)]
    if limit and page:
        return results[limit*page:limit*(page+1)]
    elif limit:
        return results[:limit]
    return results


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
    return Response(status_code=204)


async def drop_user_privileges_impl(
        user: Union[int, str],
        issuer: Union[int, str, None],
        local: LocalRequestData,
        transform_func: Callable[[models.User], models.User]
) -> models.User:
    """
    Internal implementation to simply drop user privileges using a hook function
    """

    user = await resolve_user_spec(user, local)
    if user.special:
        raise Conflict("The community user can't drop other user's privileges")
    if not user.active:
        raise Conflict("The user is already disabled, dropping privileges isn't necessary.")
    if issuer is not None:
        issuer = await resolve_user_spec(issuer, local)
        if user != issuer:
            raise BadRequest("You are not allowed to drop another user's privileges!")
    user = transform_func(user)
    local.session.add(user)
    local.session.commit()
    return user
