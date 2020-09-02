#!/usr/bin/env python3

import datetime
import json
import telegram
import argparse

from state import get_or_create_user
from .base import BaseCommand


class HistoryCommand(BaseCommand):

    def __init__(self):
        super().__init__("history")
        self.parser.add_argument("offset", nargs="?", default=0, type=int)
        self.parser.add_argument("count", nargs="?", default=10, type=int)

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        user = get_or_create_user(msg.from_user)
        entries = []

        with open("transactions.log", "r") as fd:
            for line in fd.readlines():
                entry = json.loads(line)
                if entry['user'] == user['id']:
                    entries.insert(0, entry)

        texts = []
        for entry in entries[args.offset: args.soffset + args.count]:
            time = datetime.datetime.fromtimestamp(entry['timestamp']).strftime("%Y-%m-%d %H:%M")
            texts.append("{} {:.2f}€ {}".format(time, entry['diff'] / float(100), entry['reason']))

        reply = "Transaction history for {}\n{}".format(user['name'], "\n".join(texts))
        msg.reply_text(reply, disable_notification=True)
