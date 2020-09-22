"""
Collection of parser argument types
See actions.Action's type parameter
"""

import re
from typing import Type

from mate_bot.state.user import MateBotUser
from mate_bot.state.finders import find_user_by_username
from mate_bot.commands.base import BaseCommand
from mate_bot.config import config
from mate_bot.parsing.util import EntityString


__amount_pattern = re.compile(r"^(\d+)(?:[,.](\d)(\d)?)?$")
# Regex explanation:
# It matches any non-zero number of digits with an optional , or . followed by exactly one or two digits
# If there is a , or . then the first decimal is required
#
# The match's groups:
# 1st group: leading number, 2nd group: 1st decimal, 3rd group: 2nd decimal


BOOLEAN_POSITIVE = [
    "on",
    "1",
    "+",
    "true",
    "yes",
    "good",
    "allow",
    "allowed"
]

BOOLEAN_NEGATIVE = [
    "off",
    "0",
    "-",
    "false",
    "no",
    "bad",
    "deny",
    "denied"
]


def amount(arg: str) -> int:
    """
    Convert the string into an amount of money.

    If the result is not between ``min_amount`` and ``max_amount``
    (including them), a ``ValueError`` will be raised.

    :param arg: string to be parsed
    :type arg: str
    :return: Amount of money in cent
    :rtype: int
    :raises ValueError: when the arg seems to be no valid amount or is out of the allowed range
    """

    min_amount = 0
    max_amount = config["general"]["max-amount"]

    match = __amount_pattern.match(arg)
    if match is None:
        raise ValueError("Doesn't match an amount's regex")

    val = int(match.group(1)) * 100
    if match.group(2):
        val += int(match.group(2)) * 10
    if match.group(3):
        val += int(match.group(3))

    if val == 0:
        raise ValueError("An amount can't be zero")
    elif val > max_amount:
        raise ValueError("The amount is too high")
    elif val < min_amount:
        raise ValueError("The amount is too low")

    return val


def boolean(arg: str) -> bool:
    """
    Convert the string into a boolean using allowed phrases (word lists)

    :param arg: string to be parsed
    :type arg: str
    :return: properly converted boolean value
    :rtype: bool
    :raises ValueError: when the argument could not be converted properly
    """

    if arg.lower() in BOOLEAN_POSITIVE and not arg.lower() in BOOLEAN_NEGATIVE:
        return True
    if arg.lower() in BOOLEAN_NEGATIVE and not arg.lower() in BOOLEAN_POSITIVE:
        return False
    raise ValueError("Unknown boolean phrase.")


def natural(arg: str) -> int:
    """
    Convert the string into a natural number (positive integer)

    :param arg: string to be parsed
    :type arg: str
    :return: only positive integers
    :rtype: int
    :raises ValueError: when the string seems to be no integer or is not positive
    """

    result = int(arg)
    if result <= 0:
        raise ValueError("Not a positive integer.")
    return result


def user(arg: EntityString) -> MateBotUser:
    """
    Convert the string into a MateBot user as defined in the ``state`` package

    :param arg: string to be parsed
    :type arg: str
    :return: fully functional MateBot user
    :rtype: MateBotUser
    :raises ValueError: when the argument does not start with @ or @@
    """

    if arg.entity is None:
        raise ValueError('No user mentioned. Try with "@".')

    elif arg.entity.type == "mention":
        usr = find_user_by_username(arg)
        if usr is None:
            raise ValueError("Ambiguous username. Please send /start to the bot privately.")
        return usr

    elif arg.entity.type == "text_mention":
        return MateBotUser(arg.entity.user)

    else:
        raise ValueError('No user mentioned. Try with "@".')


def command(arg: str) -> Type[BaseCommand]:
    """
    Convert the string into a command class

    :param arg: string to be parsed
    :type arg: str
    :return: the command's class
    :rtype: Type[BaseCommand]
    :raises ValueError: when the command is unknown
    """

    if arg in BaseCommand.COMMAND_DICT:
        return BaseCommand.COMMAND_DICT[arg]
    else:
        raise ValueError("Unknown command")
