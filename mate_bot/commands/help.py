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
from mate_bot.state.user import MateBotUser


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
            msg = self.get_help_for_command(args.command)
        else:
            commands = "\n".join(map(lambda c: f" - `{c}`", sorted(registry.commands.keys())))
            msg = f"{self.usage}\n\nList of commands:\n\n{commands}"
            user = MateBotUser(update.effective_message.from_user)
            if user.external:
                msg += "\n\nYou are an external user. Some commands may be restricted."
                if user.creditor is None:
                    msg += (
                        "\nYou don't have any creditor. Your possible interactions "
                        "with the bot are very limited for security purposes. You "
                        "can ask some internal user to act as your voucher. To "
                        "do this, the internal user needs to execute `/vouch "
                        "<your username>`. Afterwards, you may use this bot."
                    )

        if msg == "":
            update.effective_message.reply_text(
                "Sadly, no help is available for this command yet."
            )
        else:
            update.effective_message.reply_markdown(msg)

    @staticmethod
    def get_help_for_command(command: BaseCommand) -> str:
        """
        Get the help message for a specific command in Markdown

        :param command: command which should be used for help message generation
        :type command: BaseCommand
        :return: Markdown-enabled help message for a specific command
        :rtype: str
        """

        usages = "\n".join(map(lambda x: f"`/{command.name} {x}`", command.parser.usages))
        return f"*Usages:*\n{usages}\n\n*Description:*\n{command.description}"


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
