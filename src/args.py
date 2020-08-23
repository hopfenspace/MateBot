#!/usr/bin/env python3

import re
from typing import List, Dict, Any, Callable
from telegram import Message

from config import config
from state import get_or_create_user, find_user_by_nick


class ParsingError(Exception):
    pass


def parse_abstract_arg(arg: str, i: int, msg: Message, offset: int, unparsed: List[str]) -> Any:
    """
    A dummy function for ``parseArgs``' types.

    Any ``parseArgs``' type will be called with these parameter.

    :param arg: String to be parsed
    :type arg: str
    :param i: Index of ``arg``'s position, primarily used in error messages
    :type i: int
    :param msg: Telegram's message object being parsed
    :type msg: Message
    :param offset: Starting position of ``arg`` in the original message's string
    :type offset: int
    :param unparsed: The following and therefore still unparsed arguments.
        Use ``.pop()`` to consume more than one argument
    :type unparsed: List[str]
    :raises ParsingError:
    :return: Parsed value
    :rtype: Any
    """

    pass


def parse_text_arg(arg: str, i: int, msg: Message, offset: int, unparsed: List[str]) -> str:
    """
    Simply return the argument as string.

    :param arg: String to be parsed
    :type arg: str
    :param i: Index of ``arg``'s position, primarily used in error messages
    :type i: int
    :param msg: Telegram's message object being parsed
    :type msg: Message
    :param offset: Starting position of ``arg`` in the original message's string
    :type offset: int
    :param unparsed: The following and therefore still unparsed arguments.
        Use ``.pop()`` to consume more than one argument
    :type unparsed: List[str]
    :raises ParsingError:
    :return: ``arg``
    :rtype: str
    """

    return arg


def parse_int_arg(arg: str, i: int, msg: Message, offset: int, unparsed: List[str]) -> int:
    """
    Try converting the argument string into an integer.

    :param arg: String to be parsed
    :type arg: str
    :param i: Index of ``arg``'s position, primarily used in error messages
    :type i: int
    :param msg: Telegram's message object being parsed
    :type msg: Message
    :param offset: Starting position of ``arg`` in the original message's string
    :type offset: int
    :param unparsed: The following and therefore still unparsed arguments.
        Use ``.pop()`` to consume more than one argument
    :type unparsed: List[str]
    :raises ParsingError:
    :return: Parsed integer
    :rtype: int
    """

    try:
        return int(arg)
    except ValueError:
        raise ParsingError("Argument {} should be an int but is '{}'".format(i, arg))


def parse_amount_arg(arg: str, i: int, msg: Message, offset: int, unparsed: List[str],
                     min_amount: float = 0, max_amount: float = config["max-amount"]) -> int:
    """
    Convert the string into an amount of money.

    If the result is not between ``min_amount`` and ``max_amount`` (including them), an ParsingError will be raised.

    :param arg: String to be parsed
    :type arg: str
    :param i: Index of ``arg``'s position, primarily used in error messages
    :type i: int
    :param msg: Telegram's message object being parsed
    :type msg: Message
    :param offset: Starting position of ``arg`` in the original message's string
    :type offset: int
    :param unparsed: The following and therefore still unparsed arguments.
        Use ``.pop()`` to consume more than one argument
    :type unparsed: List[str]
    :param min_amount: The amount has to be larger than this (given in €)
    :type min_amount: float, optional
    :param max_amount: The amount has to be smaller than this (given in €)
    :type max_amount float, optional
    :raises ParsingError:
    :return: Amount of money in cent
    :rtype: int
    """

    # Regex explanation:
    # It matches any non-zero number of digits with an optional , or . followed by exactly one or two digits
    # If there is a , or . then the first decimal is required
    #
    # The match's groups:
    # 1st group: leading number, 2nd group: 1st decimal, 3rd group: 2nd decimal
    match = re.match(r"^(\d+)(?:[,.](\d)(\d)?)?$", arg)
    if match is None:
        raise ParsingError("Argument {} doesn't match an amount's regex".format(i))

    val = int(match.group(1)) * 100
    if match.group(2):
        val += int(match.group(2)) * 10
    if match.group(3):
        val += int(match.group(3))

    if val == 0:
        raise ParsingError("Argument {} should be an amount but is zero".format(i))
    elif val > max_amount * 100:
        raise ParsingError("Argument {} should be an amount but is larger than the maximum allowed amount".format(i))
    elif val < min_amount * 100:
        raise ParsingError("Argument {} should be an amount but is smaller than the minimum allowed amount".format(i))

    return val


def parse_user_arg(arg: str, i: int, msg: Message, offset: int, unparsed: List[str]) -> Dict:
    """
    Return a user as defined in ``state.py``

    :param arg: String to be parsed
    :type arg: str
    :param i: Index of ``arg``'s position, primarily used in error messages
    :type i: int
    :param msg: Telegram's message object being parsed
    :type msg: Message
    :param offset: Starting position of ``arg`` in the original message's string
    :type offset: int
    :param unparsed: The following and therefore still unparsed arguments.
        Use ``.pop()`` to consume more than one argument
    :type unparsed: List[str]
    :raises ParsingError:
    :return: Parsed user
    :rtype: Any
    """

    for entity in msg.entities:
        if entity.offset == offset:
            if entity.type == "mention":
                return find_user_by_nick(arg[1:])
            elif entity.type == "text_mention":
                return get_or_create_user(entity.user)
    else:
        raise ParsingError("Argument {} should be an user but is '{}'".format(i, arg))


def parse_rest_arg(arg: str, i: int, msg: Message, offset: int, unparsed: List[str]) -> str:
    """
    Consume all unparsed arguments and add them into one string (separated by space)

    :param arg: String to be parsed
    :type arg: str
    :param i: Index of ``arg``'s position, primarily used in error messages
    :type i: int
    :param msg: Telegram's message object being parsed
    :type msg: Message
    :param offset: Starting position of ``arg`` in the original message's string
    :type offset: int
    :param unparsed: The following and therefore still unparsed arguments.
        Use ``.pop()`` to consume more than one argument
    :type unparsed: List[str]
    :raises ParsingError:
    :return: Parsed value
    """

    # Pop all items from unparsed and combine them with arg before giving this list to " ".join
    # The pop operations have to be done in order to empty the unparsed
    return " ".join([arg] + [unparsed.pop(0) for _ in range(len(unparsed))])


ARG_TEXT = parse_text_arg
ARG_INT = parse_int_arg
ARG_AMOUNT = parse_amount_arg
ARG_USER = parse_user_arg
ARG_REST = parse_rest_arg


def parse_args(msg: Message, arg_types: List[Callable], defaults: List[Any], usage: str = "") -> List[Any]:
    """
    Parse a message string for arguments contained.

    If an error occurs, its error message will be replied back to the msg and raised.

    :param msg: the incoming message
    :param arg_types: a list of constants defining which type of argument should be at its position
    :param defaults: a list of values to use if the ``msg`` is shorter than ``arg_types`` might expect
    :param usage: a string appended to error messages
    :raises Exception:
    :return: a list of values contained in the ``msg``
    """

    try:
        unparsed = msg.text.split(" ")
        result = []

        command = unparsed.pop(0)
        offset = len(command) + 1  # + 1 for the split away space

        for i, arg_type in enumerate(arg_types):
            if len(unparsed) > 0:
                arg = unparsed.pop(0)
            elif i < len(defaults) and defaults[i] is not None:
                result.append(defaults[i])
                continue
            else:
                raise ParsingError("Argument {} not specified".format(i))

            result.append(arg_type(arg, i, msg, offset, unparsed))

            offset += len(arg) + 1  # + 1 for the split away space

        return result

    except ParsingError as error:
        error_msg = str(error) + usage
        msg.reply_text(error_msg)
        raise ParsingError(error_msg)
