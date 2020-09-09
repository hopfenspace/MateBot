import argparse

import telegram

from mate_bot import state
from mate_bot.commands.base import BaseCommand


class DataCommand(BaseCommand):
    """
    Command executor for /data
    """

    def __init__(self):
        super().__init__("data", "")
        self.parser.add_argument("trash-bin", nargs="*")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if update.effective_message.chat.type != "private":
            update.effective_message.reply_text("This command can only be used in private chat.")
            return

        user = state.MateBotUser(update.effective_message.from_user)
        result = (
            f"Overview over currently stored data for {user.name}:\n"
            f"\n```\n"
            f"User ID: {user.uid}\n"
            f"Telegram ID: {user.tid}\n"
            f"Name: {user.name}\n"
            f"Username: {user.username}\n"
            f"Balance: {user.balance / 100 :.2f}€\n"
            f"Vote permissions: {user.permission}\n"
            f"External user: {user.external}\n"
            f"Creditor user: {None if user.creditor is None else state.MateBotUser(user.creditor).name}\n"
            f"Account created: {user.created}\n"
            f"Last transaction: {user.accessed}\n"
            f"```\n"
            f"Use the /history command to see your transaction log."
        )

        update.effective_message.reply_markdown(result)
