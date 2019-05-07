from state import getOrCreateUser, createTransaction

def drink(bot, update):
	user = getOrCreateUser(update.message.from_user)
	createTransaction(user, -100, "drink")
	update.message.reply_text("OK, enjoy your 🍹!", disable_notification=True)

def water(bot, update):
	user = getOrCreateUser(update.message.from_user)
	createTransaction(user, -50, "water")
	update.message.reply_text("OK, enjoy your 🍼!", disable_notification=True)

def pizza(bot, update):
	user = getOrCreateUser(update.message.from_user)
	createTransaction(user, -150, "pizza")
	update.message.reply_text("Buon appetito! 🍕", disable_notification=True)

def ice(bot, update):
	user = getOrCreateUser(update.message.from_user)
	createTransaction(user, -50, "ice")
	update.message.reply_text("Have a sweet one! 🚅", disable_notification=True)
