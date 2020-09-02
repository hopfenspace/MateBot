#!/usr/bin/env python3

import argparse

import telegram

import state
from .base import BaseCommand


class BalanceCommand(BaseCommand):

    def __init__(self):
        super().__init__("balance")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = state.MateBotUser(update.effective_message.from_user)
        update.effective_message.reply_text("Your balance is: {:.2f}€".format(user.balance / 100))
