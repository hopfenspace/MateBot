"""
MateBot command executor classes for /pay and its callback queries
"""

import argparse

import telegram

from mate_bot.commands.common_util import user_list_to_string
from mate_bot.commands.base import BaseCommand
from mate_bot.args.types import amount as amount_type
from mate_bot.args.actions import JoinAction
from mate_bot.currency import format_money

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

    def __str__(self):
        return f"Pay by {self.creator['name']}\n" \
               f"Amount: {format_money(self.amount)}\n" \
               f"Reason: {self.reason}\n" \
               f"Approvers: {user_list_to_string(self.approved)}\n" \
               f"Disapprovers: {user_list_to_string(self.disapproved)}\n"


class PayCommand(BaseCommand):

    def __init__(self):
        super().__init__("pay", "")
        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", action=JoinAction, nargs="*")

    def run(self, args: argparse.Namespace, msg: telegram.Message) -> None:
        """
        sender = get_or_create_user(msg.from_user)
        sender_id = str(sender['id'])

        if sender_id in pays:
            msg.reply_text("You already have a pay in progress")
            return

        user_pay = Pay(sender, args.amount, args.sreason)
        user_pay.message = msg.reply_text(str(user_pay), reply_markup=user_pay.message_markup)
        pays[sender_id] = user_pay
        """


class PayQuery:
    pass


"""
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
        #create_transaction(selected_pay.creator, selected_pay.amount,
        #                   "pay for {}, approved by {}".format(selected_pay.reason, user_list_to_string(selected_pay.approved)))
        selected_pay.message.edit_text("APPROVED\n" + str(selected_pay))
    elif changed:
        selected_pay.message.edit_text(str(selected_pay), reply_markup=selected_pay.message_markup)
    else:
        update.callback_query.answer()
"""
