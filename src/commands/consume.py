#!/usr/bin/env python3

from state import get_or_create_user, create_transaction
import random


def drink(_, update):
    user = get_or_create_user(update.message.from_user)
    create_transaction(user, -100, "drink")
    update.message.reply_text("OK, enjoy your 🍹!", disable_notification=True)


hydrationMessages = [
    "OK, enjoy your 🍼!",
    "HYDRATION! 💦",
    "Hydrier dich!",
    "Hydrieren sie sich bitte!",
    "Der Bahnbabo sagt: Hydriert euch! 💪"
]


def water(_, update):
    user = get_or_create_user(update.message.from_user)
    create_transaction(user, -50, "water")
    update.message.reply_text(random.choice(hydrationMessages), disable_notification=True)


def pizza(_, update):
    user = get_or_create_user(update.message.from_user)
    create_transaction(user, -200, "pizza")
    update.message.reply_text("Buon appetito! 🍕", disable_notification=True)


def ice(_, update):
    user = get_or_create_user(update.message.from_user)
    create_transaction(user, -50, "ice")
    update.message.reply_text("Have a sweet one! 🚅", disable_notification=True)
