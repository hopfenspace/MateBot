#!/usr/bin/env python3

import telegram
import argparse

from .base import BaseCommand
from ..state import MateBotUser


class BalanceCommand(BaseCommand):

    def __init__(self):
        super().__init__("balance")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        user = MateBotUser(update.effective_message.from_user)
        update.effective_message.reply_text("Your balance is: {:.2f}€".format(user.balance / 100))
