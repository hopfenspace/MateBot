"""
MateBot command executor classes for /zwegat
"""

import argparse

import telegram

from mate_bot.state.user import CommunityUser
from mate_bot.commands.base import BaseCommand
from mate_bot.money_formatter import format_money


class ZwegatCommand(BaseCommand):
    """
    Command executor for /zwegat
    """

    def __init__(self):
        super().__init__("zwegat", "Show the central funds.")

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
            update.effective_message.reply_text(f"Peter errechnet ein massives Vermögen von {format_money(total)}")
        else:
            update.effective_message.reply_text(f"Peter errechnet Gesamtschulden von {format_money(-total)}")
