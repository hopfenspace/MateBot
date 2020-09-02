#!/usr/bin/env python3

import telegram
import argparse

from .common_util import user_list_to_string, get_data_from_query
from .base import BaseCommand
from state import get_or_create_user, create_transaction
from args import amount as amount_type
from args import JoinAction

communisms = {}


class Communism:
    def __init__(self, creator, amount, reason):
        self.creator = creator
        self.amount = amount
        self.reason = reason
        self.members = [creator]
        self.message = None
        self.externs = 0

        prefix = "communism " + str(creator['id'])
        self.message_markup = telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("JOIN/LEAVE", callback_data=prefix + " join/leave"),
            ],
            [
                telegram.InlineKeyboardButton("EXTERN -", callback_data=prefix + " extern-"),
                telegram.InlineKeyboardButton("EXTERN +", callback_data=prefix + " extern+"),
            ],
            [
                telegram.InlineKeyboardButton("OK", callback_data=prefix + " ok"),
                telegram.InlineKeyboardButton("CANCEL", callback_data=prefix + " cancel"),
            ],
        ])

    def amount_euro(self):
        return self.amount / float(100)

    def update_text(self):
        self.message.edit_text(str(self), reply_markup=self.message_markup)

    def __str__(self):
        return "Communism by {}\nAmount: {:.2f}€\nReason: {}\nExterns: {}\nCommunists: {}\n" \
            .format(self.creator['name'], self.amount_euro(), self.reason, self.externs,
                    user_list_to_string(self.members))


class CommunismCommand(BaseCommand):

    def __init__(self):
        super().__init__("/communism")
        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", action=JoinAction)

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        sender = get_or_create_user(msg.from_user)
        sender_id = str(sender['id'])

        if sender_id in communisms:
            msg.reply_text("You already have a communism in progress")
            return

        user_communism = Communism(sender, args.amount, args.reason)
        user_communism.message = msg.reply_text(str(user_communism), reply_markup=user_communism.message_markup)
        communisms[sender_id] = user_communism


def communism_query(_, update):
    sender, selected_communism, cmd, sender_id, action = get_data_from_query(update, communisms)

    members = selected_communism.members
    is_admin = sender == selected_communism.creator

    if action == "join/leave":
        if sender in members:
            members.remove(sender)
        else:
            members.append(sender)

        if len(members) == 0:
            del communisms[split[1]]
            selected_communism.message.edit_text("Everyone left, the communism died")
        else:
            selected_communism.update_text()
    elif is_admin and action == "ok":
        count = len(members) + selected_communism.externs
        amount = selected_communism.amount // count

        # if the amount can't be split equally everyone pays 1 cent more
        if selected_communism.amount % count != 0:
            amount = amount + 1

        reason = "communism by " + selected_communism.creator['name']
        for member in members:
            create_transaction(member, -amount, reason)

        payout = selected_communism.amount - selected_communism.externs * amount
        create_transaction(selected_communism.creator, payout, reason)
        del communisms[split[1]]

        creator = selected_communism.creator['name']
        amountf = amount / float(100)
        text = "Communism by {}\n{} paid {:.2f}\n{} received {:.2f}\n{:.2f} has to be collected from {} externs\nDescription: {}" \
            .format(creator, user_list_to_string(selected_communism.members), amountf,
                    creator, payout / float(100), amountf, selected_communism.externs, selected_communism.reason)
        selected_communism.message.edit_text(text)

    elif is_admin and action == "cancel":
        del communisms[sender_id]
        selected_communism.message.edit_text("Communism canceled")

    elif is_admin and action == "extern-":
        if selected_communism.externs > 0:
            selected_communism.externs -= 1
            selected_communism.update_text()
        else:
            update.message.reply_text("Cannot reduce externs below zero")

    elif is_admin and action == "extern+":
        selected_communism.externs += 1
        selected_communism.update_text()
