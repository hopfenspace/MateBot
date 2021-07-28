"""
Generic helper library for the core REST API
"""

from typing import List, Type

import pydantic

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
