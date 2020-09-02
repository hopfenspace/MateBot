#!/usr/bin/env python3

import telegram
import argparse

from state import get_or_create_user, create_transaction
from .base import BaseCommand
from args import amount as amount_type
from args import user as user_type


class SendCommand(BaseCommand):

    def __init__(self):
        super().__init__("send")
        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("receiver", type=user_type)

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        sender = get_or_create_user(msg.from_user)

        if sender == args.receiver:
            msg.reply_text("You cannot send money to yourself")
            return

        create_transaction(sender, -args.amount, "sent to {}".format(args.receiver['name']))
        create_transaction(args.receiver, args.amount, "received from {}".format(sender['name']))
        msg.reply_text("OK, you sent {}€ to {}".format(args.amount / float(100), args.receiver['name']))
