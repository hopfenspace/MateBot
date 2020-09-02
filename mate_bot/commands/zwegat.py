#!/usr/bin/env python3

import telegram
import argparse

from state import users
from .base import BaseCommand


class ZwegatCommand(BaseCommand):

    def __init__(self):
        super().__init__("zwegat")

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        total = 0
        for user_id in users:
            total += users[user_id]["balance"]

        total = float(total) / 100
        if total <= 0:
            msg.reply_text("Peter errechnet ein massives Vermögen von {:.2f}€".format(-1 * total))
        else:
            msg.reply_text("Peter errechnet Gesamtschulden von {:.2f}€".format(total))
