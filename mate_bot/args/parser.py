#!/usr/bin/env python3

"""
MateBot argument parsing helper library
"""

from argparse import Namespace, ArgumentParser
from typing import Optional, Sequence

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
    """

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
            self.error("unrecognized argument{} {}".format(
                "s" if len(argv) > 1 else "",
                " ".join(argv)
            ))
        return args

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

        raise RuntimeError("The parser for \"{}\" tried to exit".format(self.prog))

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

        raise ParsingError(message, self.format_usage())
