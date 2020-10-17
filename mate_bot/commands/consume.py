"""
MateBot command executor classes for any kind of consuming action
"""

import logging
import random as _random
import typing as _typing

import telegram

from mate_bot.state.user import MateBotUser, CommunityUser
from mate_bot.parsing.types import natural as natural_type
from mate_bot.config import config
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.util import Namespace
from mate_bot.state.transactions import LoggedTransaction


logger = logging.getLogger("commands")


class ConsumeCommand(BaseCommand):
    """
    Base class for consumption executors

    Subclasses of this class should only overwrite
    the constructor in order to implement a new command.
    """

    def __init__(self, name: str, description: str, price: int, messages: _typing.List[str], symbol: str):
        """
        :param name: name of the command
        :type name: str
        :param price: money amount in Cent that a user has to pay for the consumable
        :type price: int
        :param symbol: UTF-8 emoticon that is displayed `n` times
        :type symbol; str
        :param messages: list of messages that the bot replies as confirmation
        :type messages: typing.List[str]
        """

        super().__init__(name, description)
        if not self.description:
            self.description = f"Consume {name}s for {price / 100 :.2f}€ each."

        self.parser.add_argument("number", default=1, type=natural_type, nargs="?")

        self.price = price
        self.messages = messages
        self.symbol = symbol

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = MateBotUser(update.effective_message.from_user)
        if not self.ensure_permissions(sender, 1, update.effective_message):
            return

        if args.number > config["general"]["max-consume"]:
            update.effective_message.reply_text(
                "You can't consume that many goods at once!"
            )
            return

        reason = f"consume: {args.number}x {self.name}"
        LoggedTransaction(
            sender,
            CommunityUser(),
            self.price * args.number,
            reason,
            update.effective_message.bot
        ).commit()

        update.effective_message.reply_text(
            _random.choice(self.messages) + self.symbol * args.number,
            disable_notification=True
        )
