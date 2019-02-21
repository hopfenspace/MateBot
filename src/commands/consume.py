from state import getOrCreateUser, createTransaction

def drink(bot, update):
	user = getOrCreateUser(update.message.from_user)
	createTransaction(user, -100, "drink")
	update.message.reply_text("OK, enjoy your drink!", disable_notification=True)
