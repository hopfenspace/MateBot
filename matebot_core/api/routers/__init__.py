"""
MateBot router modules for handling requests to various endpoints

This module exports the list ``all_routers`` which includes a list of all
routers of all submodules of that package. Note that the "generic" router
is the first in the list, whereas all others are sorted alphabetically.
"""

from .aliases import router as aliases_router
from .applications import router as applications_router
from .callbacks import router as callbacks_router
from .communisms import router as communisms_router
from .consumables import router as consumables_router
from .generic import router as generic_router
from .polls import router as polls_router
from .refunds import router as refunds_router
from .transactions import router as transactions_router
from .users import router as users_router
from .votes import router as votes_router


all_routers = [
    generic_router,
    aliases_router,
    applications_router,
    callbacks_router,
    communisms_router,
    consumables_router,
    polls_router,
    refunds_router,
    transactions_router,
    users_router,
    votes_router
]
