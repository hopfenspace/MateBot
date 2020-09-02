#!/usr/bin/env python3

"""
MateBot command handling base library
"""

import sys
import argparse
from traceback import print_exc as _print_exc

import telegram.ext

from args import NonExitingParser, ParsingError, pre_parse


class BaseCommand:
    """
    Base class for all MateBot commands executed by the CommandHandler

    It handles argument parsing and exception catching / handling. Some
    specific implementation should be a subclass of this class. It must add
    arguments to the parser in the constructor and overwrite the run method.
    """

    def __init__(self, name: str):
        """
        :param name: name of the command
        :type name: str
        """

        self.name = name
        self.parser = NonExitingParser(prog=name)

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        Perform command-specific actions

        This method should be overwritten in actual commands to perform the desired action.

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseCommand.run() method in a subclass")

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        Parse arguments of the incoming update and execute the .run() method

        This method is the callback method used by telegram.CommandHandler.
        Note that this method also catches any exceptions and prints them.

        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        """

        try:
            argv = pre_parse(update.effective_message)
            args = self.parser.parse_args(argv)
            self.run(args, update)
        except ParsingError as err:
            update.effective_message.reply_text(str(err))
        finally:
            if sys.exc_info()[0] is not None:
                _print_exc()
