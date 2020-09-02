#!/usr/bin/env python3

from args import NonExitingParser
from args import ParsingError
from args import pre_parse
from traceback import print_exc
import argparse
import telegram


class BaseCommand:
    """
    Base class for all commands given to a CommandHandler.

    It handles argument parsing and exception catching/ handling.
    A command should inherit this, add arguments to the parser in the constructor and overwrite the run method.
    """

    def __init__(self, name: str):
        self.name = name
        self.parser = NonExitingParser(prog=name)

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        """
        This method should be overwritten in actual commands to perform the desired action.

        :param args: The namespace containing the arguments
        :type args: argparse.Namespace
        :param msg: The message to reply to
        :type msg: telegram.Message
        :raises NotImplementedError: this method should be overwritten by subclasses
        """
        raise NotImplementedError("The BaseCommand's run method should be overwritten by subclasses")

    def __call__(self, bot: telegram.Bot, update: telegram.Update) -> None:
        """
        The callback the telegram.CommandHandler uses.

        Parse the arguments and call the run method.
        Catch any occurring exceptions.

        :param bot:
        :type bot: telegram.Bot
        :param update:
        :type update: telegram.Update
        """
        try:
            argv = pre_parse(update.message)
            args = self.parser.parse_args(argv)
            self.run(args, update.message)
        except ParsingError as err:
            update.message.reply_text(str(err))
        except:
            print_exc()
