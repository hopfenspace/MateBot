"""
MateBot command executor classes for /vouch
"""

import argparse

import telegram

from mate_bot.args import types
from mate_bot.commands.base import BaseCommand


class VouchCommand(BaseCommand):
    """
    Command executor for /vouch
    """

    def __init__(self):
        super().__init__(
            "vouch",
            "Internal users can vouch for externals to allow them to use this bot. "
            "Otherwise, the possibilities would be very limited for security purposes."
        )

        self.parser.add_argument("user", nargs="?", type=types.user)

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        update.effective_message.reply_text("This feature is not implemented yet.")
