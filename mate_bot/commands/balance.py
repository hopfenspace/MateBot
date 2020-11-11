"""
MateBot command executor classes for /balance
"""

import logging

import telegram

from mate_bot.state.user import MateBotUser
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.types import user as user_type
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class BalanceCommand(BaseCommand):
    """
    Command executor for /balance
    """

    def __init__(self):
        super().__init__(
            "balance",
            "Use this command to show a user's balance.\n\n"
            "When you use this command without arguments, the bot will "
            "reply with your current amount of money stored in your virtual "
            "wallet. If you specify a username or mention someone as an argument,"
            "the 'balance' of this user is returned instead of yours."
        )

        self.parser.add_argument("user", type=user_type, nargs="?")

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.user:
            user = args.user
            update.effective_message.reply_text(f"Balance of {user.name} is: {user.balance / 100 : .2f}€")

        else:
            user = MateBotUser(update.effective_message.from_user)
            update.effective_message.reply_text(f"Your balance is: {user.balance / 100 :.2f}€")
