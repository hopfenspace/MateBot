import argparse

import telegram

from mate_bot import state
from mate_bot.commands.base import BaseCommand


class DataCommand(BaseCommand):
    """
    Command executor for /data
    """

    def __init__(self):
        super().__init__("data", "Request the data the bot has stored about you.\n\n"
                                 "This command can only be used in private chat to protect private data.\n"
                                 "To view your transactions use `/history`.")
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

        if user.external:
            if user.creditor:
                creditor = state.MateBotUser(user.creditor)
                relations = f"Creditor user: {creditor.name}"
                if creditor.username:
                    relations += f" ({creditor.username})"
            else:
                relations = "Creditor user: None"

        else:
            users = ", ".join(map(
                lambda u: f"{u.name} ({u.username})" if u.username else u.name,
                map(
                    lambda i: state.MateBotUser(i),
                    user.debtors
                )
            ))
            if len(users) == 0:
                users = "None"
            relations = f"Debtor user{'s' if len(users) != 1 else ''}: {users}"

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
            f"{relations}\n"
            f"Account created: {user.created}\n"
            f"Last transaction: {user.accessed}\n"
            f"```\n"
            f"Use the /history command to see your transaction log."
        )

        update.effective_message.reply_markdown(result)
