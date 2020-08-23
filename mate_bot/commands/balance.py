#!/usr/bin/env python3

from state import get_or_create_user


def balance(_, update):
    user = get_or_create_user(update.message.from_user)
    balance_user = float(user['balance']) / 100
    update.message.reply_text("Your balance is: {:.2f}€".format(balance_user))
