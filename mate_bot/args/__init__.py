#!/usr/bin/env python3

"""
MateBot library to easily parse arguments of commands
"""

from .parser import NonExitingParser
from .types import amount, natural, user
from .actions import JoinAction
from .pre_parser import pre_parse


__all__ = [
    "NonExitingParser",
    "amount",
    "natural",
    "user",
    "JoinAction",
    "pre_parse"
]
