from state import getOrCreateUser, createTransaction
import random
from args import parseArgs, ARG_INT


def getAmountHelper(msg, name) -> int:
	args = parseArgs(msg, [ARG_INT], [1], "/{} [amount]".format(name))
	if isinstance(args[0], int):
		if args[0] == 0:
			msg.reply_text("You can't consume zero {}s".format(name))
			return 0
		elif args[0] < 0:
			msg.reply_text("You can't consume a negative number of {}s".format(name))
			return 0
		elif args[0] > 10:
			msg.reply_text("You can't consume more than 10 {}s at once!".format(name))
			return 0
		return args[0]
	else:
		msg.reply_text("Unknown parsing error")
		return 0


def drink(bot, update):
	num = getAmountHelper(update.message, "drink")
	if num > 0:
		user = getOrCreateUser(update.message.from_user)
		createTransaction(user, -100 * num, "drink x{}".format(num))
		update.message.reply_text("OK, enjoy your {}!".format(num * '🍹'), disable_notification=True)


hydrationMessages = [
	("OK, enjoy your {}!", "🍼"),
	("HYDRATION! {}", "🍶"),
	("Hydrier dich! {}", "💦"),
	("Hydrieren sie sich bitte! {}", "💧"),
	("Der Bahnbabo sagt: Hydriert euch! {}", "💪")
]


def water(bot, update):
	num = getAmountHelper(update.message, "water")
	if num > 0:
		user = getOrCreateUser(update.message.from_user)
		createTransaction(user, -50 * num, "water x{}".format(num))
		answer = random.choice(hydrationMessages)
		update.message.reply_text(answer[0].format(num * answer[1]), disable_notification=True)


def pizza(bot, update):
	num = getAmountHelper(update.message, "pizza")
	if num > 0:
		user = getOrCreateUser(update.message.from_user)
		createTransaction(user, -200 * num, "pizza x{}".format(num))
		update.message.reply_text("Buon appetito! {}".format(num * '🍕'), disable_notification=True)


def ice(bot, update):
	num = getAmountHelper(update.message, "ice")
	if num > 0:
		user = getOrCreateUser(update.message.from_user)
		createTransaction(user, -50 * num, "ice x{}".format(num))
		update.message.reply_text("Have a sweet one! {}".format(num * '🚅'), disable_notification=True)
