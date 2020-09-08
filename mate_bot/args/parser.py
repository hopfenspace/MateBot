"""
MateBot's custom `ArgumentParser`
"""

import sys as _sys
from argparse import Namespace, ArgumentParser, Action, ArgumentTypeError, ArgumentError, HelpFormatter
from typing import Optional, Sequence, Any, Type

from err import ParsingError


class PatchedParser(ArgumentParser):
    """
    PatchedParser is an ArgumentParser with some patches to work with this bot

    List of patches:
    * The ArgumentParser of the `argparse` module would exit the program
      when an error occurs. This is fine in the context of shells where each
      command is a stand-alone program and the program should exit when it
      doesn't understand what to do. But this is a bot handling multiple
      commands. It can't just stop when a user messes up the syntax.
      Therefore, this class overwrites the .error() and .exit() methods
      of the original `ArgumentParser` class from the `argparse` module.
    * The error message for unrecognized arguments didn't differentiate between singular and plural.
      It always used plural. This class doesn't. It only adds the plural s if there are more than one
      unrecognized arguments.
    * Type conversion errors weren't treated equally. argparse dumps ValueError and TypeError's error messages
      while forwarding ArgumentTypeError's error messages. This class treats all equally and forwards them for all
      of these three error types.
    * The help argument will not be added in the constructor.

    :param prog: the commands name (without /)
    :type prog: str
    """
    
    def __init__(self, prog: str):
        super(PatchedParser, self).__init__(prog=prog, add_help=False)

    def parse_args(
            self,
            args: Optional[Sequence[str]] = None,
            namespace: Optional[Namespace] = None
    ) -> Namespace:
        """
        Convert argument strings to objects and assign them as attributes of the namespace.

        Patch:
        The original error messages for unrecognized arguments didn't differentiate between a single
        unrecognized argument and multiple ones. The message always used the plural.

        :param args: a sequence of arguments to parse
        :type args: Optional[Sequence[str]]
        :param namespace: an optinal Namespace to populate
        :type namespace: Optional[Namespace]
        :return: the populated Namespace
        :rtype: Namespace
        """

        # This annoyed CrsiX. So we changed it.
        args, argv = self.parse_known_args(args, namespace)
        if argv:
            self.error(f"unrecognized argument{'s' if len(argv) > 1 else ''} {' '.join(argv)}")
        return args

    def _get_value(self, action: Action, arg_string: str) -> Any:
        """
        This method uses tries to convert an argument to its specified type.

        Patch:
        Originally there was a distinction between argparse's ArgumentTypeErrors and python's Value- and TypeErrors.
        The error messages for the python ones were dumped an replace by a simple "invalid value".
        Now it uses the same code for all those errors.

        :param action: the action used for the argument
        :type action: Action
        :param arg_string: the argument string to convert
        :type arg_string: str
        :return: the converted value
        :rtype: Any
        """

        type_func = self._registry_get("type", action.type, action.type)
        if not callable(type_func):
            raise ArgumentError(action, f"{repr(type_func)} is not callable")

        # convert the value to the appropriate type
        try:
            result = type_func(arg_string)

        # ArgumentTypeErrors, TypeError and ValueError indicate errors
        except (ArgumentTypeError, TypeError, ValueError):
            name = getattr(action.type, "__name__", repr(action.type))
            msg = str(_sys.exc_info()[1])
            raise ArgumentError(action, msg)

        # return the converted value
        return result

    def exit(self, status: int = 0, message: str = None) -> None:
        """
        This method originally terminated the program, exiting with the specified status and, if given,
        it prints a message before that.

        Patch:
        This method shouldn't be called anymore at all. Therefore it raises a RuntimeError if it is.

        :param status: the exit status
        :type status: int
        :param message: a message to be printed before exiting
        :type message: str
        :raises RuntimeError: when called
        """

        raise RuntimeError(f"The parser for \"{self.prog}\" tried to exit")

    def error(self, message: str) -> None:
        """
        This method originally printed a usage message including the message to the standard error
        and terminated the program with a status code of 2.

        Patch:
        When an error occurs (its while parsing) and an error message should be given to the user. But the user is now
        a telegram user and not someone on the command line. So this method now just raises an ParsingError to be caught
        and send to the user by the commands.

        :param message: the error message
        :type message: type
        :raises ParsingError: when called
        """

        raise ParsingError(message)
