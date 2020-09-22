"""
Helper function for creating usage strings
"""

from mate_bot.parsing.actions import Action


def get_metavar(action: Action) -> str:
    """
    Get an action's metavar

    :param action:
    :type action: argparse.Action
    :return: metavar
    :rtype: str
    """
    if action.metavar is not None:
        return action.metavar
    # elif action.choices is not None:
    #     return " | ".join(map(repr, action.choices))
    else:
        return action.dest


def format_action(action: Action) -> str:
    """
    Format a single argument

    :param action: the argument to get the formatted string for
    :type action: argparse.Action
    :return: action as formatted string
    :rtype: str
    """
    metavar = get_metavar(action)
    nargs = action.nargs

    # if action.choices is not None:
    #     arg = "({})"
    if isinstance(nargs, int) and action.nargs > 0:
        arg = " ".join("<{0}>" for _ in range(nargs))
    else:
        try:
            arg = {
                None: "<{}>",
                "?":  "[{}]",
                "*":  "[{} ...]",
                "+":  "<{} ...>"
            }[nargs]
        except KeyError:
            raise ValueError(f"unsupported nargs: {nargs}")

    return arg.format(metavar)
