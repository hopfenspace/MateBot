"""
MateBot command executor classes for /help
"""

import telegram

from mate_bot.commands.base import BaseCommand
from mate_bot.commands.registry import COMMANDS
from mate_bot.parsing.types import command as command_type
from mate_bot.parsing.util import Namespace


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
            msg = args.command.description
        else:
            commands = "\n".join(map(lambda c: f" - `{c}`", sorted(COMMANDS.commands_as_dict.keys())))
            msg = f"{self.usage}\n\nList of commands:\n\n{commands}\n"

        if msg == "":
            update.effective_message.reply_text(
                "Sadly, no help is available for this command yet."
            )
        else:
            update.effective_message.reply_markdown(msg)
