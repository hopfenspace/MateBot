"""
MateBot schemas for updating pieces of existing models
"""

from typing import List, Optional, Union

import pydantic

from .bases import UserAlias


class UpdatingCommunism(pydantic.BaseModel):
    id: pydantic.NonNegativeInt
    active: bool
    accepted: Optional[bool]
    externals: pydantic.NonNegativeInt
    participants: List[Union[pydantic.NonNegativeInt, UserAlias]]
