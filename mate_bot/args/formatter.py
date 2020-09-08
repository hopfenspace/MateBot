"""

"""

import argparse
from argparse import OPTIONAL, ZERO_OR_MORE, ONE_OR_MORE, REMAINDER, PARSER, SUPPRESS

from .actions import JoinAction


def _format_arg(action: argparse.Action) -> str:
    """
    Format a single argument

    :param action: the argument to get the formatted string for
    :type action: argparse.Action
    :return: action as formatted string
    :rtype: str
    """

    if action.metavar is not None:
        metavar = action.metavar
    # elif action.choices is not None
    else:
        if action.option_strings:
            metavar = action.dest.upper()
        else:
            metavar = action.dest

    if action.nargs is None:
        arg = "<{}>"
    elif action.nargs == OPTIONAL:
        arg = "[{}]"
    elif action.nargs == ZERO_OR_MORE:
        arg = "[{} ...]"
    elif action.nargs == ONE_OR_MORE:
        arg = "<{} ...>"
    elif action.nargs == REMAINDER:
        raise NotImplementedError("nargs == REMAINDER is not implemented")
    elif action.nargs == PARSER:
        raise NotImplementedError("nargs == PARSER is not implemented")
    elif action.nargs == SUPPRESS:
        raise NotImplementedError("nargs == SUPPRESS is not implemented")
    elif isinstance(action.nargs, int) and action.nargs > 0:
        arg = " ".join("<{0}>" for i in range(action.nargs))
    else:
        raise ValueError("unsupported nargs: {}".format(action.nargs))

    return arg.format(metavar)


def format_usage(parser: argparse.ArgumentParser) -> str:
    """
    Create the usage string for a parser.

    :param parser: the argument parser
    :type parser: argparse.ArgumentParser
    :return: the usage string
    :rtype: str
    """
    token = [parser.prog] + list(map(_format_arg, parser._actions))

    return "Usage: `{}`".format(" ".join(token))
