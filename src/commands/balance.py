from state import getOrCreateUser

def balance(bot, update):
	user = getOrCreateUser(update.message.from_user)
	balance = float(user['balance']) / 100
	update.message.reply_text("Your balance is: {}€".format(balance))
