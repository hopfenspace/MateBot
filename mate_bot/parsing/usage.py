from mate_bot.parsing.util import Representable
from mate_bot.parsing.actions import Action, StoreAction
from mate_bot.parsing.formatting import format_action
from mate_bot.parsing.types import _bot_command


class CommandUsage(Representable):
    """
    A CommandUsage represents a command's use case.

    A command can have multiple use cases with conflicting arguments.
    These objects hold the arguments for one such use case and the parser
    tries which usage applies to a given set of arguments.
    """

    def __init__(self):
        self._actions = []
        self.add_argument("bot_command", type=_bot_command, nargs="?", metavar="")

    @property
    def actions(self):
        return self._actions

    @property
    def min_arguments(self) -> int:
        """
        Return the minimum required amount of arguments.
        """
        return sum(map(lambda x: x.min_args, self._actions))

    @property
    def max_arguments(self) -> int:
        """
        Return the maximum allowed amount of arguments
        """
        return sum(map(lambda x: x.max_args, self._actions))

    def add_argument(self, dest: str, **kwargs) -> Action:
        if "action" in kwargs:
            action_type = kwargs["action"]
            del kwargs["action"]
        else:
            action_type = StoreAction

        self._actions.append(action_type(dest, **kwargs))

        return self._actions[0]

    def __str__(self):
        """
        Return the usage string
        """
        return " ".join(filter(bool, map(format_action, self._actions)))
