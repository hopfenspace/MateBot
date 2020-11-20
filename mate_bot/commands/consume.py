"""
MateBot command executor classes for any kind of consuming action
"""

import logging
import random as _random
import typing as _typing

from nio import MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.state import User, Transaction
from mate_bot.parsing.types import natural as natural_type
from mate_bot.config import config
from mate_bot.commands.base import BaseCommand, VOUCHED
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class ConsumeCommand(BaseCommand):
    """
    Base class for consumption executors

    Subclasses of this class should only overwrite
    the constructor in order to implement a new command.
    """

    def __init__(self, name: str, description: str, description_formatted: str, price: int, messages: _typing.List[str], symbol: str):
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

        super().__init__(name, description, description_formatted)
        if not self.description:
            self.description = f"Consume {name}s for {price / 100 :.2f}€ each."
        if not self.description_formatted:
            self.description_formatted = f"Consume {name}s for {price / 100 :.2f}€ each."

        self.parser.add_argument("number", default=1, type=natural_type, nargs="?")

        self.price = price
        self.messages = messages
        self.symbol = symbol

    async def run(self, args: Namespace, api: ApiWrapper, room: MatrixRoom, event: RoomMessageText) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param api: the api to respond with
        :type api: hopfenmatrix.api_wrapper.ApiWrapper
        :param room: room the message came in
        :type room: nio.MatrixRoom
        :param event: incoming message event
        :type event: nio.RoomMessageText
        :return: None
        """
        sender = await self.get_sender(api, room, event)

        if not await self.ensure_permissions(sender, VOUCHED, api, event, room):
            return

        if args.number > config.general.max_consume:
            msg = "You can't consume that many goods at once!"

        else:
            Transaction.perform(
                sender,
                User.community_user(),
                self.price * args.number,
                f"consume: {args.number}x {self.name}"
            )
            msg = _random.choice(self.messages) + self.symbol * args.number

        await api.send_reply(msg, room, event, send_as_notice=True)
