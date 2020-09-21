"""
MateBot command executor classes for /send
"""

import argparse

import telegram

from mate_bot import state
from mate_bot.args.types import amount as amount_type
from mate_bot.args.types import user as user_type
from mate_bot.commands.base import BaseCommand


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

        def e(variant: str) -> str:
            return f"send {variant} {args.amount} {sender.uid} {args.receiver.uid}"

        update.effective_message.reply_text(
            f"Do you want to send {args.amount / 100 :.2f}€ to {str(args.receiver)}?"
            f"\nDescription: `{reason}`",
            reply_markup = telegram.InlineKeyboardMarkup([
                [
                    telegram.InlineKeyboardButton("CONFIRM", callback_data = e("confirm")),
                    telegram.InlineKeyboardButton("ABORT", callback_data = e("abort"))
                ]
            ]),
            parse_mode = "Markdown"
        )
