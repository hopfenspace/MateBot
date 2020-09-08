import argparse
import random as _random
import typing as _typing

from typing import List as _List
from typing import Dict as _Dict
from typing import Union as _Union
from typing import Type as _Type

import telegram

import state
from args.types import natural as natural_type
from config import config
from .base import BaseCommand


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

        super().__init__(name, "`/{} [number]`".format(name), description)
        self.parser.add_argument("number", default=1, type=natural_type, nargs="?")

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


def dynamic_consumable(consumable: _Dict[str, _Union[str, int, _List[str]]]) -> _Type[ConsumeCommand]:
    """
    Create a dynamic consume command from a dict.

    The dict should contain the `ConsumeCommand.__init__`'s parameters:
    * name
    * description
    * price
    * messages
    * symbol

    Why is this function necessary? Couldn't one just give the dict as keyword arguments to the `__init__`?
    Yes with our current implementation this is necessary, because the BaseCommand a command's class
    to be used by the `/help` command. Therefore each consume command needs it's own class and this function
    creates them at runtime.

    Example of such a dict:
    ```json
    {
        "name": "ice",
        "messages": [
             "Ok, enjoy your ice!",
             "Mhmm, yummy!"
        ],
        "symbol": "U+1F368",
        "description": "Get an ice.",
        "price": 50
    }
    ```
    :param consumable: a dict containing the required information
    :type consumable: Dict[str, Union[str, int, List[str]]]
    :return: a dynamically created consume command
    :rtype: Type[ConsumeCommand]
    """

    class DynamicConsume(ConsumeCommand):

        def __init__(self):
            super(DynamicConsume, self).__init__(
                consumable["name"],
                consumable["description"],
                consumable["price"],
                consumable["messages"],
                consumable["symbol"]
            )

    return DynamicConsume
