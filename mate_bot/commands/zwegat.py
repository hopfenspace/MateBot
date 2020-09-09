import argparse

import telegram

from mate_bot.state import users
from mate_bot.commands.base import BaseCommand


class ZwegatCommand(BaseCommand):

    def __init__(self):
        super().__init__("zwegat", "")

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        total = 0
        for user_id in users:
            total += users[user_id]["balance"]

        total = float(total) / 100
        if total <= 0:
            msg.reply_text(f"Peter errechnet ein massives Vermögen von {-1 * total :.2f}€")
        else:
            msg.reply_text(f"Peter errechnet Gesamtschulden von {total :.2f}€")
