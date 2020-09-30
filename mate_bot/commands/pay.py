"""
MateBot command executor classes for /pay and its callback queries
"""

import telegram

from mate_bot.commands.base import BaseCommand, BaseCallbackQuery
from mate_bot.parsing.types import amount as amount_type
from mate_bot.parsing.actions import JoinAction
from mate_bot.parsing.util import Namespace

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
        raise NotImplementedError


class PayCommand(BaseCommand):

    def __init__(self):
        super().__init__("pay", "The `/pay` command enables users who spend money for the community to get"
                                " their money back. Using /pay <amount> <reason> you can claim you bought"
                                " something for the community. Others have to approve before the money goes"
                                " to your account.")
        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", action=JoinAction, nargs="*")

    def run(self, args: Namespace, msg: telegram.Message) -> None:
        pass


class PayQuery(BaseCallbackQuery):
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
        # "pay for {}, approved by {}".format(selected_pay.reason, user_list_to_string(selected_pay.approved)))
        selected_pay.message.edit_text("APPROVED\n" + str(selected_pay))
    elif changed:
        selected_pay.message.edit_text(str(selected_pay), reply_markup=selected_pay.message_markup)
    else:
        update.callback_query.answer()
"""
