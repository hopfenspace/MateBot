from state import users


def zwegat(bot, update):
    total = 0
    for id in users:
        total -= users[id]["balance"]

    total = -1 * float(total) / 100
    if total <= 0:
        update.message.reply_text(
            "Peter errechnet ein massives Vermögen von {}€".format(total * (-1)))
    else:
        update.message.reply_text(
            "Peter errechnet Gesamtschulden von {}€".format(total))
