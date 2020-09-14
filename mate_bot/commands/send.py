"""
MateBot command executor classes for /send
"""

import argparse

import telegram

from mate_bot import state
from mate_bot.args.types import amount as amount_type
from mate_bot.args.types import user as user_type
from mate_bot.commands.base import BaseCommand
from mate_bot.currency import format_money


class SendCommand(BaseCommand):
    """
    Command executor for /send
    """

    def __init__(self):
        super().__init__("send", "Send money to another user.")
        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("receiver", type=user_type)
        self.parser.add_argument("reason", default="<no description>", nargs="*")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = state.MateBotUser(update.effective_message.from_user)
        if isinstance(args.reason, list):
            reason = "send: " + " ".join(args.reason)
        else:
            reason = "send: " + args.reason

        if sender == args.receiver:
            update.effective_message.reply_text("You can't send money to yourself!")
            return

        trans = state.Transaction(sender, args.receiver, args.amount, reason)
        trans.commit()

        update.effective_message.reply_text(
            f"Okay, you sent {format_money(args.amount)} to {str(args.receiver)}"
        )
