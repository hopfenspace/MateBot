import telegram
from state import get_or_create_user, create_transaction, user_list_to_string
from args import parse_args, ARG_AMOUNT, ARG_REST

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


def communism(_, update):
    amount, reason = parse_args(update.message,
                                [ARG_AMOUNT, ARG_REST],
                                [None, ""],
                                "\nUsage: /communism <amount> [reason ...]")

    sender = get_or_create_user(update.message.from_user)
    sender_id = str(sender['id'])

    if sender_id in communisms:
        update.message.reply_text("You already have a communism in progress")
        return

    user_communism = Communism(sender, amount, reason)
    user_communism.message = update.message.reply_text(str(user_communism), reply_markup=user_communism.message_markup)
    communisms[sender_id] = user_communism


def communism_query(_, update):
    sender = get_or_create_user(update.callback_query.from_user)
    split = update.callback_query.data.split(" ")

    if len(split) != 3:
        print(split)
        raise Exception("invalid callback query")
    elif split[1] not in communisms:
        print(split)
        raise Exception("invalid ID")

    selected_communism = communisms[split[1]]
    members = selected_communism.members
    is_admin = sender == selected_communism.creator

    if split[2] == "join/leave":
        if sender in members:
            members.remove(sender)
        else:
            members.append(sender)

        if len(members) == 0:
            del communisms[split[1]]
            selected_communism.message.edit_text("Everyone left, the communism died")
        else:
            selected_communism.update_text()
    elif is_admin and split[2] == "ok":
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

    elif is_admin and split[2] == "cancel":
        del communisms[split[1]]
        selected_communism.message.edit_text("Communism canceled")

    elif is_admin and split[2] == "extern-":
        if selected_communism.externs > 0:
            selected_communism.externs -= 1
            selected_communism.update_text()
        else:
            update.message.reply_text("Cannot reduce externs below zero")

    elif is_admin and split[2] == "extern+":
        selected_communism.externs += 1
        selected_communism.update_text()
