"""

"""

import argparse
from argparse import OPTIONAL, ZERO_OR_MORE, ONE_OR_MORE, REMAINDER, PARSER, SUPPRESS


def _get_metavar(action: argparse.Action) -> str:
    """
    Get an action's metavar

    :param action:
    :type action: argparse.Action
    :return: metavar
    :rtype: str
    """
    if action.metavar is not None:
        return action.metavar
    # elif action.choices is not None
    else:
        if action.option_strings:
            return action.dest.upper()
        else:
            return action.dest


def _format_arg(action: argparse.Action) -> str:
    """
    Format a single argument

    :param action: the argument to get the formatted string for
    :type action: argparse.Action
    :return: action as formatted string
    :rtype: str
    """
    metavar = _get_metavar(action)

    if action.help == SUPPRESS:
        return None
    elif action.nargs is None:
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
        raise ValueError(f"unsupported nargs: {action.nargs}")

    return arg.format(metavar)


def format_usage(parser: argparse.ArgumentParser) -> str:
    """
    Create the usage string for a parser.

    :param parser: the argument parser
    :type parser: argparse.ArgumentParser
    :return: the usage string
    :rtype: str
    """
    token = ["/" + parser.prog] + list(filter(bool, map(_format_arg, parser._actions)))

    return f"Usage: `{' '.join(token)}`"
