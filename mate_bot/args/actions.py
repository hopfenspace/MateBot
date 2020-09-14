"""
Collection of parser actions
See `argparse.ArgumentParser.add_argument`'s action parameter

There is:
* `JoinAction`: join an arbitrary number of strings with spaces
* `MutExAction`: simulate a mutually exclusive argument group for positional arguments
"""

import argparse
import typing

from mate_bot.args.formatter import _get_metavar


class JoinAction(argparse.Action):
    """
    This action takes strings and joins them with spaces.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=str,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if type is not str:
            raise ValueError("type has to be str")
        super().__init__(option_strings, dest, nargs, const, default, type, choices, required, help, metavar)
       
    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 values: typing.List[str],
                 option_string: str = None):
        setattr(namespace, self.dest, " ".join(values))


class MutExAction(argparse.Action):
    """
    This action is a workaround for mutually exclusive positional arguments.

    It kind of simulates an mutually exclusive group but for positional arguments.

    Conditions:
    - The positional arguments must be optional (nargs = "?" or "*").
    - This action has to be the last. Any after it will not be reachable.
    - The contained action have to be added after this one

    How it works:
    - It will iterate over all its actions (in order of adding)
    - For each action it will check if the argument strings would match the action
    - If it matches, this action be executed

    This means that an action, whose possible argument strings are accepted
    by a previous one as well, will never be used. So any action added after an
    action with `type=str` and `nargs="*"` will not be reached.

    Example:
    ```
    >>> parser = ArgumentParser()
    >>> mut = parser.add_argument("foo", action=MutExAction)
    >>> mut.add_action(parser.add_argument("int", type=int, nargs="?"))
    >>> mut.add_action(parser.add_argument("str", type=str, nargs="?"))
    >>>
    >>> parser.parse_args(["text"])
    Namespace(foo=None, int=None, str="text")
    >>> parser.parse_args(["2"])
    Namespace(foo=None, int=2, str=None)
    ```
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 metavar=None,
                 **kwargs):
        super(MutExAction, self).__init__(option_strings,
                                          dest,
                                          nargs="*",
                                          const=None,
                                          default=None,
                                          type=str,
                                          choices=None,
                                          metavar=metavar,
                                          required=False)
        self._actions = []
        self._metavar = metavar
        self.formatting_nargs = nargs

    def add_action(self, action: argparse.Action):
        """
        Add an action to this group.

        :param action: action to add
        :type action: argparse.Action
        """
        self._actions.append(action)

        # Hide the action
        action.help = argparse.SUPPRESS

        # Store the original default because it will be overwritten
        action.original_default = action.default

    @property
    def metavar(self):
        """
        Get this action's metavar

        If it was given in the constructor, use that.
        Elif there are actions, concatenate their metavars.
        Else use this action's dest (argparse default).
        """

        if self._metavar is not None:
            return self._metavar
        elif self._actions:
            return " | ".join(map(_get_metavar, self._actions))
        else:
            return self.dest

    @metavar.setter
    def metavar(self, value):
        """
        This will be used in Action's __init__ but shouldn't do anything.
        """

        pass

    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 value_strings: typing.List[str],
                 option_string: str = None):

        # Make sure the original defaults are used
        for action in self._actions:
            action.default = action.original_default

        # If no arguments where given do nothing, all actions will get their defaults
        if not value_strings:
            return

        # Find a applicable action
        for action in self._actions:

            # If the action doesn't want arguments it should be skipped
            if action.nargs is argparse.SUPPRESS:
                continue

            # Try to convert the values and see if it works
            try:
                # The following is a simplified parser._get_values
                if action.nargs not in [argparse.PARSER, argparse.REMAINDER]:
                    try:
                        value_strings.remove('--')
                    except ValueError:
                        pass

                values = [parser._get_value(action, v) for v in value_strings]
                if action.nargs == argparse.REMAINDER:
                    pass
                elif action.nargs == argparse.PARSER:
                    parser._check_value(action, values[0])
                else:
                    for v in values:
                        parser._check_value(action, v)
            # If it doesn't, this is not the correct action
            except argparse.ArgumentError:
                continue

            # If the action expects a single argument, not a list
            if action.nargs in [None, argparse.OPTIONAL]:
                if len(values) == 1:
                    values = values[0]
                elif len(values) > 1:
                    raise argparse.ArgumentError(action, f"too many arguments: {' '.join(value_strings[1:])}")

            # Execute the action
            action(parser, namespace, values, option_string)

            # Overwrite the default
            # argparse will write it to the namespace
            # because it thinks the action hasn't appeared
            action.default = getattr(namespace, action.dest)
            break

        # If no applicable action is found
        else:
            raise argparse.ArgumentError(self, f"Found no applicable action for: {value_strings}")
