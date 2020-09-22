"""
MateBot library responsible for parsing incoming messages
"""

from mate_bot.parsing.parser import CommandParser
from mate_bot.parsing.util import Namespace

__all__ = [
    "CommandParser",
    "Namespace"
]
