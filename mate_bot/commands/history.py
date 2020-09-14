import argparse

import telegram

from mate_bot import state
from mate_bot.args.types import natural as natural_type
from mate_bot.args.actions import MutExAction
from mate_bot.commands.base import BaseCommand


class HistoryCommand(BaseCommand):
    """
    Command executor for /history
    """

    def __init__(self):
        super().__init__("history", "")
        mut = self.parser.add_argument("length_export", action=MutExAction, nargs="?")
        mut.add_action(self.parser.add_argument("length", nargs="?", default=10, type=natural_type))
        mut.add_action(self.parser.add_argument("export", nargs="?", type=str, choices=("json", "csv")))


    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = state.MateBotUser(update.effective_message.from_user)
        logs = state.TransactionLog(user).to_string()
        if len(logs) == 0:
            update.effective_message.reply_text("You don't have any registered transactions yet.")
            return

        log = logs.split("\n")
        answer = "\n".join(log[-args.length:])
        update.effective_message.reply_markdown_v2(
            f"Transaction history for {user.name}:\n```\n{answer}```",
            disable_notification=True
        )
