"""
MateBot router modules for handling requests to various endpoints

This module exports the list ``all_routers`` which includes a list of all
routers of all submodules of that package. Note that the "generic" router
is the first in the list, whereas all others are sorted alphabetically.
"""

from .aliases import router as aliases_router
from .callbacks import router as callbacks_router
from .communisms import router as communisms_router
from .login import router as login_router
from .polls import router as polls_router
from .readonly import router as readonly_router
from .refunds import router as refunds_router
from .transactions import router as transactions_router
from .users import router as users_router


all_routers = [
    login_router,
    readonly_router,
    aliases_router,
    callbacks_router,
    communisms_router,
    polls_router,
    refunds_router,
    transactions_router,
    users_router
]
