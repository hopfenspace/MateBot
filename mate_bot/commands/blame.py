#!/usr/bin/env python3

import argparse
import telegram
from .base import BaseCommand
from state import MateBotUser


class BlameCommand(BaseCommand):
    """
    Command executor for /blame
    """

    def __init__(self):
        super(BlameCommand, self).__init__("blame", "`/blame`", "")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        debtors = MateBotUser.get_worst_debtors()
        if len(debtors) == 1:
            msg = "The user with the highest debt is:\n"
        else:
            msg = "The users with the highest debts are:\n"
        msg += "\n".join(map(lambda x: x.username if x.username else x.name, debtors))
