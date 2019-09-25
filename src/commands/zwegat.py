from state import users

def zwegat(bot, update):
	total = 0
	for id in users:
		total -= users[id]["balance"]

	total = -1 * float(total) / 100
	update.message.reply_text("Peter errechnet Gesamtschulden von {}€".format(total))
