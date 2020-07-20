from state import users


def zwegat(_, update):
    total = 0
    for user_id in users:
        total += users[user_id]["balance"]

    total = float(total) / 100
    if total <= 0:
        update.message.reply_text("Peter errechnet ein massives Vermögen von {}€".format(-1 * total))
    else:
        update.message.reply_text("Peter errechnet Gesamtschulden von {}€".format(total))
