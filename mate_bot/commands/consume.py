#!/usr/bin/env python3

from state import get_or_create_user, create_transaction
from .base import BaseCommand
import random
import argparse
import telegram


class ConsumeCommand(BaseCommand):

    def __init__(self, name, price, messages):
        super().__init__(name)
        self.price = price
        self.messages = messages

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        user = get_or_create_user(msg.from_user)
        create_transaction(user, -self.price, self.name)

        if len(self.messages) == 1:
            msg.reply_text(self.messages[0], disable_notification=True)
        elif len(self.messages) > 1:
            msg.reply_text(random.choice(self.messages), disable_notification=True)


class DrinkCommand(ConsumeCommand):

    def __init__(self):
        super().__init__("drink", 100, ["OK, enjoy your 🍹!"])


class WaterCommand(ConsumeCommand):

    def __init__(self):
        super().__init__("water", 50, [
            "OK, enjoy your 🍼!",
            "HYDRATION! 💦",
            "Hydrier dich!",
            "Hydrieren sie sich bitte!",
            "Der Bahnbabo sagt: Hydriert euch! 💪"
        ])


class PizzaCommand(ConsumeCommand):

    def __init__(self):
        super().__init__("pizza", 200, ["Buon appetito! 🍕"])


class IceCommand(ConsumeCommand):

    def __init__(self):
        super().__init__("ice", 50, "Have a sweet one! 🚅")
