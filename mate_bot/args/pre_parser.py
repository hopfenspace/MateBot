#!/usr/bin/env python3

"""
A function to prepare a message for parsing with the actual parser
"""

import telegram
import typing


def pre_parse(msg: telegram.Message) -> typing.Iterator[str]:
    """
    Fill the message string with additional information and split it.

    The problem solved by this function is the following:
    argparse is made for terminal use and therefore expects a string containing all relevant information.
    Telegram's messages contain information in the entities attribute which can't be obtained from the string alone.

    As example this is problematic when a mentioned user has no nickname. When he does, there will be an @ followed
    by the nickname in the string. A user without nickname can have any string and is undetectable and
    unidentifiable.

    :param msg: the message to be processed
    :type msg: telegram.Message
    :return: a list to be given to a parser's parse_args
    :rtype: typing.Iterator[str]
    """

    text = msg.text

    for entity in reversed(msg.entities):
        # String to replace the entity with
        replace = None

        # Check if the entity should be replaced and by what
        if entity.type == "bot_command":
            replace = ""
        if entity.type == "text_mention":
            replace = "@@" + str(entity.user.id)

        # Perform the replacement
        if replace is not None:
            text = text[:entity.offset] + replace + text[entity.offset + entity.length:]

    # split the input text by spaces then filter out empty strings
    # example: " foo    bar  baz" -> ["foo", "bar", "baz"]
    # this is the same behaviour as bash and fish
    # TODO don't split "\ "
    return filter(bool, text.split(" "))
