"""
Collection of parser argument types.
See :class:`mate_bot.parsing.actions.Action`'s type parameter
"""

import re

from mate_bot import registry
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


def amount(arg: str) -> int:
    """
    Convert the string into an amount of money.

    A maximum allowed amount, this function accepts, is set in the config.

    :param arg: string to be parsed
    :type arg: str
    :return: Amount of money in cent
    :rtype: int
    :raises ValueError: when the arg seems to be no valid amount or is too big
    """

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
    elif val > config["general"]["max-amount"]:
        raise ValueError("The amount is too high")

    return val


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
    :type arg: EntityString
    :return: fully functional MateBot user
    :rtype: MateBotUser
    :raises ValueError: when username is ambiguous or the argument wasn't a mention
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


def command(arg: str) -> BaseCommand:
    """
    Convert the string into a command with this name

    :param arg: the desired command's name
    :type arg: str
    :return: the command
    :rtype: BaseCommand
    :raises ValueError: when the command is unknown
    """

    try:
        return registry.commands[arg.lower()]
    except KeyError:
        raise ValueError(f"{arg} is an unknown command")
