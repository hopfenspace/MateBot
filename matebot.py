import json, datetime, traceback
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

with open("config.json", "r") as fd:
	config = json.load(fd)

with open("state.json", "r") as fd:
	users = json.load(fd)

logFd = open("transactions.log", "a")

def saveState():
	with open("state.json", "w") as fd:
		json.dump(users, fd)

def createTransaction(user, diff, reason):
	log = {
		'timestamp': datetime.datetime.now().timestamp(),
		'from': user["id"],
		'diff': diff,
		'reason': reason
	}
	logFd.write(json.dumps(log) + '\n')
	logFd.flush()

	user['balance'] += diff
	saveState()

def getOrCreateUser(user):
	id = str(user.id)
	if id not in users:
		users[id] = {
			'id': user.id,
			'name': user.full_name,
			'nick': user.username,
			'balance': 0
		}
		saveState()

	return users[id]

def findUserByNick(nick):
	for id in users:
		user = users[id]
		if user['nick'] == nick:
			return user

	return None

def parseAmount(text, min=0, max=config["max-amount"]):
	try:
		val = float(text)
		if val > 0 and val <= max and int(val * 100) / float(100) == val:
			return int(val * 100)
		else:
			return None
	except:
		return None

ARG_TEXT = 0
ARG_AMOUNT = 1
ARG_USER = 2
ARG_REST = 3
def parseArgs(msg, argDef, usage=""):
	split = msg.text.split(" ")
	result = []
	error = None

	offset = len(split[0]) + 1
	split = split[1 : ]

	for i, expected in enumerate(argDef):
		if i < len(split):
			arg = split[i]
		else:
			arg = ""

		if expected == ARG_TEXT:
			result.append(arg)
		elif expected == ARG_AMOUNT:
			val = parseAmount(arg)
			if val is None:
				error = "Argument {} should be an amount but is '{}'".format(i, arg)
				break
			result.append(val)
		elif expected == ARG_USER:
			user = None
			for entity in msg.entities:
				print(offset, arg, entity.offset)
				if entity.offset == offset:
					if entity.type == "mention":
						user = findUserByNick(arg[1 : ])
						break
					elif entity.type == "text_mention":
						user = getOrCreateUser(entity.user)
						break

			if user is None:
				error = "Argument {} should be an user but is '{}'".format(i, arg)
				break

			result.append(user)
		elif expected == ARG_REST:
			result.append(split[i : ])
			break

		offset = offset + len(arg) + 1

	if error is None:
		return result
	else:
		error = error + usage
		msg.reply_text(error)
		raise Exception(error)



def balance(bot, update):
	user = getOrCreateUser(update.message.from_user)
	balance = float(user['balance']) / 100
	update.message.reply_text("Your balance is: {}€".format(balance))

def drink(bot, update):
	user = getOrCreateUser(update.message.from_user)
	createTransaction(user, -100, "drink")
	update.message.reply_text("OK, enjoy your drink!")

def send(bot, update):
	args = parseArgs(update.message, [ARG_AMOUNT, ARG_USER], "\nUsage: /send <amount> <user>")
	print(args)

	sender = getOrCreateUser(update.message.from_user)
	receiver = args[1]
	amount = args[0]

	createTransaction(sender, -amount, "sent to {}".format(receiver['id']))
	createTransaction(receiver, amount, "received from {}".format(sender['id']))
	update.message.reply_text("OK, you sent {}€ to {}"
		.format(amount / float(100), receiver['name']))



def communism(bot, update):
	pass #TODO



updater = Updater(config["bot-token"])

def tryWrap(func):
	def wrapper(*args, **kwargs):
		try:
			func(*args, **kwargs)
		except:
			print(traceback.format_exc())

	return wrapper

updater.dispatcher.add_handler(CommandHandler("balance", tryWrap(balance)))
updater.dispatcher.add_handler(CommandHandler("drink", tryWrap(drink)))
updater.dispatcher.add_handler(CommandHandler("send", tryWrap(send)))

updater.start_polling()
updater.idle()
