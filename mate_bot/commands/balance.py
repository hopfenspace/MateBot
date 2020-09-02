#!/usr/bin/env python3

import telegram
import argparse
from state import get_or_create_user
from .base import BaseCommand


class BalanceCommand(BaseCommand):

    def __init__(self):
        super().__init__("balance")

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        user = get_or_create_user(msg.from_user)
        balance = float(user['balance']) / 100
        msg.reply_text("Your balance is: {:.2f}€".format(balance))
