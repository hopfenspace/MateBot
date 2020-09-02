#!/usr/bin/env python3

import argparse
import random as _random
import typing as _typing

import telegram

import state
from args import natural
from config import config
from .base import BaseCommand


class ConsumeCommand(BaseCommand):
    """
    Base class for consumption executors

    Subclasses of this class should only overwrite
    the constructor in order to implement a new command.
    """

    def __init__(self, name: str, price: int, messages: _typing.List[str], symbol: str):
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

        super().__init__(name)
        self.parser.add_argument("number", default = 1, type = natural, nargs = "?")

        self.price = price
        self.messages = messages
        self.symbol = symbol

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.number > config["general"]["max-consume"]:
            update.effective_message.reply_text(
                "You can't consume that many goods at once!"
            )
            return

        sender = state.MateBotUser(update.effective_message.from_user)
        reason = "consume: {}x {}".format(args.number, self.name)

        trans = state.Transaction(
            sender,
            state.CommunityUser(),
            self.price * args.number,
            reason
        )
        trans.commit()

        update.effective_message.reply_text(
            _random.choice(self.messages) + self.symbol * args.number,
            disable_notification=True
        )


class DrinkCommand(ConsumeCommand):
    """
    Command executor for the /drink command
    """

    def __init__(self):
        super().__init__(
            "drink",
            100,
            ["Okay, enjoy your "],
            "🍹"
        )


class WaterCommand(ConsumeCommand):
    """
    Command executor for the /water command
    """

    def __init__(self):
        super().__init__(
            "water",
            50,
            [
                "Okay, enjoy your ",
                "HYDRATION! ",
                "Hydrier dich mit ",
                "Hydrieren sie sich bitte mit ",
                "Der Bahnbabo sagt: Hydriert euch mit "
            ],
            "🍼"
        )


class PizzaCommand(ConsumeCommand):
    """
    Command executor for the /pizza command
    """

    def __init__(self):
        super().__init__(
            "pizza",
            200,
            [
                "Okay, enjoy your ",
                "Buon appetito! "
            ],
            "🍕"
        )


class IceCommand(ConsumeCommand):
    """
    Command executor for the /ice command
    """

    def __init__(self):
        super().__init__(
            "ice",
            50,
            [
                "Okay, enjoy your ",
                "Hmmh, yummy... "
            ],
            "🍨"
        )
