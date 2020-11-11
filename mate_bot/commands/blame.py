"""
MateBot command executor classes for /blame
"""

import logging

import telegram

from mate_bot.commands.base import BaseCommand
from mate_bot.state.user import MateBotUser
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class BlameCommand(BaseCommand):
    """
    Command executor for /blame
    """

    def __init__(self):
        super().__init__(
            "blame",
            "Use this command to show the user(s) with the highest debts.\n\n"
            "Put the user(s) with the highest debts to the pillory and make them "
            "settle their debts, e.g. by buying stuff like new bottle crates. "
            "This command can only be executed by internal users."
        )

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = MateBotUser(update.effective_message.from_user)
        if not self.ensure_permissions(user, 2, update.effective_message):
            return

        debtors = MateBotUser.get_worst_debtors()
        if len(debtors) == 0:
            update.effective_message.reply_text(
                "Good news! No one has to be blamed, all users have positive balances!"
            )
            return

        if len(debtors) == 1:
            msg = "The user with the highest debt is:\n"
        else:
            msg = "The users with the highest debts are:\n"
        msg += "\n".join(map(lambda x: x.username if x.username else x.name, debtors))
        update.effective_message.reply_text(msg)
