import json, datetime
from state import getOrCreateUser, createTransaction

def history(bot, update):
	user = getOrCreateUser(update.message.from_user)
	entries = []

	with open("transactions.log", "r") as fd:
		for line in fd.readlines():
			entry = json.loads(line)
			if entry['user'] == user['id']:
				entries.append(entry)

	texts = []
	for entry in entries:
		time = datetime.datetime.fromtimestamp(entry['timestamp']).strftime("%Y-%m-%d %H:%M")
		texts.append("{} {}€ {}".format(time, entry['diff'] / float(100), entry['reason']))

	msg = "Transaction history for {}\n{}".format(user['name'], "\n".join(texts))
	update.message.reply_text(msg, disable_notification=True)
