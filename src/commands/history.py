import datetime
import json

from args import parse_args, ARG_INT
from state import get_or_create_user


def history(_, update):
    offset, count = parse_args(update.message,
                               [ARG_INT, ARG_INT],
                               [0, 10],
                               "\nUsage: /history [offset = 0] [count = 10]"
                               )

    user = get_or_create_user(update.message.from_user)
    entries = []

    with open("transactions.log", "r") as fd:
        for line in fd.readlines():
            entry = json.loads(line)
            if entry['user'] == user['id']:
                entries.insert(0, entry)

    texts = []
    for entry in entries[offset: offset + count]:
        time = datetime.datetime.fromtimestamp(entry['timestamp']).strftime("%Y-%m-%d %H:%M")
        texts.append("{} {}€ {}".format(time, entry['diff'] / float(100), entry['reason']))

    msg = "Transaction history for {}\n{}".format(user['name'], "\n".join(texts))
    update.message.reply_text(msg, disable_notification=True)
