"""
MateBot command executor classes for /help
"""

import logging
import datetime

import telegram

from mate_bot import registry
from mate_bot.commands.base import BaseCommand, BaseInlineQuery
from mate_bot.parsing.types import command as command_type
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class HelpCommand(BaseCommand):
    """
    Command executor for /help
    """

    def __init__(self):
        super().__init__(
            "help",
            "The `/help` command prints the help page for any "
            "command. If no argument is passed, it will print its "
            "usage and a list of all available commands."
        )
        self.parser.add_argument("command", type=command_type, nargs="?")

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.command:
            msg = "*Usages:*\n"
            msg += "\n".join(map(lambda x: f"`/{args.command.name} {x}`", args.command.parser.usages))
            msg += "\n\n" \
                   "*Description:*\n"
            msg += args.command.description
        else:
            commands = "\n".join(map(lambda c: f" - `{c}`", sorted(registry.commands.keys())))
            msg = f"{self.usage}\n\nList of commands:\n\n{commands}\n"

        if msg == "":
            update.effective_message.reply_text(
                "Sadly, no help is available for this command yet."
            )
        else:
            update.effective_message.reply_markdown(msg)


class HelpInlineQuery(BaseInlineQuery):
    """
    Get inline help messages like /help does as command
    """

    def get_result_id(self, *args) -> str:
        """
        Generate a result ID based on the current time and the static word ``help``

        :param args: ignored collection of parameters
        :return: result ID for any inline query seeking for help
        :rtype: str
        """

        return f"help-{int(datetime.datetime.now().timestamp())}"

    def get_help(self) -> telegram.InlineQueryResult:
        """
        Get the generic help message as only answer of an inline query handled by this class

        :return: help message as inline query result
        :rtype: telegram.InlineQueryResult
        """

        return self.get_result(
            "Help",
            "#TODO"
        )

    def run(self, query: telegram.InlineQuery) -> None:
        """
        Answer the inline query by providing the result of :meth:`get_help`

        :param query: inline query as part of an incoming Update
        :type query: telegram.InlineQuery
        :return: None
        """

        query.answer([self.get_help()])
