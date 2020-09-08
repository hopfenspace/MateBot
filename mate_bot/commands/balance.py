import argparse
import telegram

import state
from .base import BaseCommand
from args.types import user as user_type


class BalanceCommand(BaseCommand):
    """
    Command executor for /balance
    """

    def __init__(self):
        super().__init__("balance", "`/balance [user]`", "")
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
        else:
            user = state.MateBotUser(update.effective_message.from_user)
        update.effective_message.reply_text("Your balance is: {:.2f}€".format(user.balance / 100))
