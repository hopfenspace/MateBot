"""
Specify the use cases of a MateBot command.
"""

import typing

from mate_bot.parsing.util import Representable
from mate_bot.parsing.actions import Action, StoreAction
from mate_bot.parsing.formatting import format_action


class CommandUsage(Representable):
    """
    A CommandUsage represents a command's use case.

    A command can have multiple use cases with conflicting arguments.
    These objects hold the arguments for one such use case and the parser
    tries which usage applies to a given set of arguments.
    """

    def __init__(self):
        """"""

        self._actions = []

    @property
    def actions(self) -> typing.List[Action]:
        """
        Get the stored actions.

        :return: the stored actions
        :rtype: List[Action]
        """

        return self._actions

    @property
    def min_arguments(self) -> int:
        """
        Get the minimum required amount of arguments.

        It sums all its actions' ``min_args``.

        :return: minimum required amount of arguments
        :rtype: int
        """

        return sum(map(lambda x: x.min_args, self._actions))

    @property
    def max_arguments(self) -> int:
        """
        Get the maximum allowed amount of arguments

        It sums all its actions' ``max_args``.

        :return: maximum allowed amount of arguments
        :rtype: int
        """

        return sum(map(lambda x: x.max_args, self._actions))

    def add_argument(self, dest: str, action: typing.Type[Action] = StoreAction, **kwargs) -> Action:
        """
        Add an argument.

        The ``**kwargs`` and ``dest`` will be handed over to the action's constructor.
        So see :ref:`mate_bot.parsing.actions` for more information.

        :param dest: The name of the attribute to hold the created object(s)
        :type dest: str
        :param action: Action class to construct action object with
        :type action: Type[Action]
        """

        self._actions.append(action(dest, **kwargs))

        return self._actions[0]

    def __str__(self):
        """
        Produce the usage string

        Example:

        .. code-block::

            >>> usage = CommandUsage()
            >>> usage.add_argument("foo")
            >>> usage.add_argument("bar", nargs="+", type=int)
            >>> usage.add_argument("baz", nargs="?")
            >>> str(usage)
            '<foo> <bar ...> [baz]'

        See :ref:`mate_bot.parsing.formatting`
        for further reading on how the arguments are formatted.
        """

        return " ".join(filter(bool, map(format_action, self._actions)))
