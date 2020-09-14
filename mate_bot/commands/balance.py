"""
MateBot command executor classes for /balance
"""

import argparse

import telegram

from mate_bot import state
from mate_bot.commands.base import BaseCommand
from mate_bot.args.types import user as user_type
from mate_bot.currency import format_money

class BalanceCommand(BaseCommand):
    """
    Command executor for /balance
    """

    def __init__(self):
        super().__init__("balance", "Shows a user's balance.")
        self.parser.add_argument("user", type=user_type, nargs="?")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.user:
            user = args.user
            update.effective_message.reply_text(f"Balance of {user.name} is: {format_money(user.balance)}")
        else:
            user = state.MateBotUser(update.effective_message.from_user)
            update.effective_message.reply_text(f"Your balance is: {format_money(user.balance)}")
