from state import getOrCreateUser, createTransaction, userListToString
from args import parseArgs, ARG_AMOUNT, ARG_USER

def send(bot, update):
	args = parseArgs(update.message,
		[ARG_AMOUNT, ARG_USER],
		[None, None],
		"\nUsage: /send <amount> <user>"
	)

	sender = getOrCreateUser(update.message.from_user)
	receiver = args[1]
	amount = args[0]

	if sender == receiver:
		update.message.reply_text("You cannot send money to youself")
		return

	createTransaction(sender, -amount, "sent to {}".format(receiver['id']))
	createTransaction(receiver, amount, "received from {}".format(sender['id']))
	update.message.reply_text("OK, you sent {}€ to {}" \
		.format(amount / float(100), receiver['name']))
