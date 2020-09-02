#!/usr/bin/env python3

import argparse

import telegram

import state
from args import natural
from .base import BaseCommand


class HistoryCommand(BaseCommand):
    """
    Command executor for /history
    """

    def __init__(self):
        super().__init__("history")
        self.parser.add_argument("length", nargs="?", default=10, type=natural)

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = state.MateBotUser(update.effective_message.from_user)
        logs = state.TransactionLog(user).to_string().split("\n")
        answer = "\n".join(logs[-args.length:])
        update.effective_message.reply_text(
            "Transaction history for {}:\n{}".format(user.name, answer),
            disable_notification=True
        )
