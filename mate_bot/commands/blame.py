import argparse

import telegram

from mate_bot.commands.base import BaseCommand
from mate_bot.state import MateBotUser


class BlameCommand(BaseCommand):
    """
    Command executor for /blame
    """

    def __init__(self):
        super(BlameCommand, self).__init__("blame", "")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        debtors = MateBotUser.get_worst_debtors()
        if len(debtors) == 0:
            update.effective_message.reply_text("Good news! No one is to blame, all users have positive balances!")
            return

        if len(debtors) == 1:
            msg = "The user with the highest debt is:\n"
        else:
            msg = "The users with the highest debts are:\n"
        msg += "\n".join(map(lambda x: x.username if x.username else x.name, debtors))
        update.effective_message.reply_text(msg)
