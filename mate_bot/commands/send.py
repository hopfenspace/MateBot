#!/usr/bin/env python3

import argparse

import telegram

import state
from args import amount as amount_type, user as user_type
from .base import BaseCommand


class SendCommand(BaseCommand):
    """
    Command executor for /send
    """

    def __init__(self):
        super().__init__("send")
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
            "Okay, you sent {:.2f}€ to {}".format(args.amount / 100, str(args.receiver))
        )
