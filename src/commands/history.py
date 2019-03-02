import json, datetime
from state import getOrCreateUser, createTransaction
from args import parseArgs, ARG_INT

def history(bot, update):
	offset, count = parseArgs(update.message,
		[ARG_INT, ARG_INT],
		[0, 10],
		"\nUsage: /history [offset = 0] [count = 10]"
	)

	user = getOrCreateUser(update.message.from_user)
	entries = []

	with open("transactions.log", "r") as fd:
		for line in fd.readlines():
			entry = json.loads(line)
			if entry['user'] == user['id']:
				entries.insert(0, entry)

	texts = []
	for entry in entries[offset : offset + count]:
		time = datetime.datetime.fromtimestamp(entry['timestamp']).strftime("%Y-%m-%d %H:%M")
		texts.append("{} {}€ {}".format(time, entry['diff'] / float(100), entry['reason']))

	msg = "Transaction history for {}\n{}".format(user['name'], "\n".join(texts))
	update.message.reply_text(msg, disable_notification=True)
