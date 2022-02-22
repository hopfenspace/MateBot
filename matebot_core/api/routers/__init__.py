"""
MateBot router modules for handling requests to various endpoints

This module exports the ``router`` object which includes all known
endpoints and path operations together with their version annotations.
"""

from ._router import router

# The order of the imports defines the order of the endpoints in the OpenAPI documentation
from . import login, readonly, aliases, callbacks, communisms, polls, refunds, transactions, users
