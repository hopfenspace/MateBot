#!/usr/bin/env python3

"""
MateBot library to parse arguments of commands using `argparse`
"""

from .actions import JoinAction
from .parser import PatchedParser
from .pre_parser import pre_parse
from .types import amount, natural, user, boolean


__all__ = [
    "JoinAction",
    "PatchedParser",
    "pre_parse",
    "amount",
    "natural",
    "user",
    "boolean"
]
