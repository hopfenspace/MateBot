"""
MateBot parser's helper functions for creating usage strings
"""

from typing import Union, Collection

from mate_bot.parsing.actions import Action


def plural_s(collection: Union[int, Collection]) -> str:
    """
    Return a plural 's' if a collection requires one.

    The argument can be anything supporting `len()` or directly an integer.

    Example of use:
    
    .. code-block::

        parser = argparse.ArgumentParser()
        ...
        args, argv = parser.parse_known_args()
        print(f"Unrecognized argument{plural_s(argv)}: {argv}")

    :param collection: a collection
    :type collection: Collection
    :return: a plural 's' or an empty string
    :rtype: str
    """

    if isinstance(collection, int):
        n = collection
    else:
        n = len(collection)

    if n == 1:
        return ""
    else:
        return "s"


def get_metavar(action: Action) -> str:
    """
    Get an action's name in a usage string.

    If a the attribute ``metavar`` is set, use it.
    If not, default to ``dest``

    :param action: action to get metavar for
    :type action: Action
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
    Format a single argument.

    Get the action's metavar and determine which brackets to put around it depending on ``nargs``:

    * default: surround the name with <>

    .. code-block::

        >>> action = Action("foo")
        >>> format_action(action)
        '<foo>'

    * ``'?'``: surround the name with [ ]

    * integer N: surround the name with <> and repeat this N times:

    .. code-block::

        >>> action = Action("foo", nargs=3)
        >>> format_action(action)
        '<foo> <foo> <foo>'

    * ``'+'``: add ... after the name and surround it with <>

    .. code-block::

        >>> action = Action("foo", nargs="+")
        >>> format_action(action)
        '<foo ...>'

    * ``'*'``: add ... after the name and surround it with [ ]

    :param action: the argument to get the formatted string for
    :type action: Action
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
