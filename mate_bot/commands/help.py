#!/usr/bin/env python3

import telegram
import argparse

from .base import BaseCommand
from args.types import command as command_type


class HelpCommand(BaseCommand):
    """
    Command executor for /help
    """

    def __init__(self):
        super().__init__("help")
        self.parser.add_argument("command", type=command_type)

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """
        parser = args.command().parser
        update.effective_message.reply_text(parser.format_help())
