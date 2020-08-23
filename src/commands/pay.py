#!/usr/bin/env python3

import telegram

from config import config
from .common_util import user_list_to_string, get_data_from_query
from state import get_or_create_user, create_transaction
from args import parse_args, ARG_AMOUNT, ARG_REST

pays = {}


class Pay:
    def __init__(self, creator, amount, reason):
        self.creator = creator
        self.amount = amount
        self.reason = reason
        self.approved = []
        self.disapproved = []
        self.message = None

        prefix = "pay " + str(creator['id'])
        self.message_markup = telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("APPROVE", callback_data=prefix + " approve"),
            ],
            [
                telegram.InlineKeyboardButton("DISAPPROVE", callback_data=prefix + " disapprove"),
            ],
        ])

    def amount_euro(self):
        return self.amount / float(100)

    def __str__(self):
        return "Pay by {}\nAmount: {:.2f}€\nReason: {}\nApprovers: {}\nDisapprovers: {}\n" \
            .format(self.creator['name'], self.amount_euro(), self.reason,
                    user_list_to_string(self.approved), user_list_to_string(self.disapproved))


def pay(_, update):
    amount, reason = parse_args(update.message,
                                [ARG_AMOUNT, ARG_REST],
                                [None, ""],
                                "\nUsage: /pay <amount> [reason ...]"
                                )

    sender = get_or_create_user(update.message.from_user)
    sender_id = str(sender['id'])

    if sender_id in pays:
        update.message.reply_text("You already have a pay in progress")
        return

    user_pay = Pay(sender, amount, reason)
    user_pay.message = update.message.reply_text(str(user_pay), reply_markup=user_pay.message_markup)
    pays[sender_id] = user_pay


def pay_query(_, update):
    sender, selected_pay, cmd, sender_id, action = get_data_from_query(update, pays)

    approved = selected_pay.approved
    disapproved = selected_pay.disapproved
    changed = False

    if sender == selected_pay.creator:
        if action == "disapprove":
            del pays[sender_id]
            selected_pay.message.edit_text("Pay canceled (the creator disapproves himself).")
            return
    elif action == "approve":
        if sender not in approved:
            approved.append(sender)
            changed = True
        if sender in disapproved:
            disapproved.remove(sender)
    elif action == "disapprove":
        if sender in approved:
            approved.remove(sender)
        if sender not in disapproved:
            disapproved.append(sender)
            changed = True

    def check_list(users):
        if len(users) < config['pay-min-users']:
            return False

        has_member = False
        for user in users:
            if user['id'] in config['members']:
                has_member = True
                break

        return has_member

    if check_list(selected_pay.disapproved):
        del pays[sender_id]
        selected_pay.message.edit_text("DISAPPROVED\n" + str(selected_pay))
    elif check_list(selected_pay.approved):
        del pays[sender_id]
        create_transaction(selected_pay.creator, selected_pay.amount,
                           "pay for {}, approved by {}".format(selected_pay.reason, user_list_to_string(selected_pay.approved)))
        selected_pay.message.edit_text("APPROVED\n" + str(selected_pay))
    elif changed:
        selected_pay.message.edit_text(str(selected_pay), reply_markup=selected_pay.message_markup)
    else:
        update.callback_query.answer()
