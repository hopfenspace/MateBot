#!/usr/bin/env python3

import argparse

import telegram

import state
from .base import BaseCommand


class DataCommand(BaseCommand):
    """
    Command executor for /data
    """

    def __init__(self):
        super().__init__("data")
        self.parser.add_argument("trash-bin", nargs="*")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if update.effective_message.chat.type != "private":
            update.effective_message.reply_text("This command can only be used in private chat.")
            return

        sender = update.effective_message.from_user
        if sender.is_bot:
            return

        if state.MateBotUser.get_uid_from_tid(sender.id) is None:
            update.effective_message.reply_text("You need to /start first.")
            return

        user = state.MateBotUser(sender)
        result = (
            "Overview over currently stored data for {}:\n\n```\n"
            "User ID: {}\nTelegram ID: {}\nName: {}\nUsername: {}\nBalance: {:.2f}€\n"
            "Vote permissions: {}\nExternal user: {}\nCreditor user: {}\n"
            "Account created: {}\nLast transaction: {}\n```"
            "\nUse the /history command to see your transaction log."
        )

        update.effective_message.reply_markdown(
            result.format(
                user.name,
                user.uid,
                user.tid,
                user.name,
                user.username,
                user.balance / 100,
                user.permission,
                user.external,
                None if user.creditor is None else state.MateBotUser(user.creditor).name,
                user.created,
                user.accessed
            )
        )
