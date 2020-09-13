import argparse

import telegram

from mate_bot.state.user import CommunityUser
from mate_bot.commands.base import BaseCommand


class ZwegatCommand(BaseCommand):
    """
    Command executor for /zwegat
    """

    def __init__(self):
        super().__init__("zwegat", "")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        total = CommunityUser().balance / 100
        if total >= 0:
            update.effective_message.reply_text(f"Peter errechnet ein massives Vermögen von {total:.2f}€")
        else:
            update.effective_message.reply_text(f"Peter errechnet Gesamtschulden von {-total:.2f}€")
