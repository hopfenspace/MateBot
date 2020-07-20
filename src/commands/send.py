from state import get_or_create_user, create_transaction
from args import parse_args, ARG_AMOUNT, ARG_USER


def send(_, update):
    args = parse_args(update.message,
                      [ARG_AMOUNT, ARG_USER],
                      [None, None],
                      "\nUsage: /send <amount> <user>")

    sender = get_or_create_user(update.message.from_user)
    receiver = args[1]
    amount = args[0]

    if sender == receiver:
        update.message.reply_text("You cannot send money to yourself")
        return

    create_transaction(sender, -amount, "sent to {}".format(receiver['name']))
    create_transaction(receiver, amount, "received from {}".format(sender['name']))
    update.message.reply_text("OK, you sent {}€ to {}".format(amount / float(100), receiver['name']))
