import json, datetime, traceback
import telegram
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler

with open("config.json", "r") as fd:
	config = json.load(fd)

with open("state.json", "r") as fd:
	users = json.load(fd)

logFd = open("transactions.log", "a")

communisms = {}
pays = {}

def saveState():
	with open("state.json", "w") as fd:
		json.dump(users, fd)

def createTransaction(user, diff, reason):
	log = {
		'timestamp': datetime.datetime.now().timestamp(),
		'user': user["id"],
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

def userListToString(users):
	names = []
	for member in users:
		names.append(member['name'])

	return ", ".join(names)

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
			result.append(" ".join(split[i : ]))
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
	update.message.reply_text("OK, enjoy your drink!", disable_notification=True)

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

class Communism:
	def __init__(self, creator, amount, reason):
		self.creator = creator
		self.amount = amount
		self.reason = reason
		self.members = [creator]
		self.message = None

		prefix = "communism " + str(creator['id'])
		self.message_markup = telegram.InlineKeyboardMarkup([
			[
				telegram.InlineKeyboardButton("JOIN/LEAVE", callback_data=prefix + " join/leave"),
			],
			[
				telegram.InlineKeyboardButton("OK", callback_data=prefix + " ok"),
				telegram.InlineKeyboardButton("CANCEL", callback_data=prefix + " cancel"),
			],
		])

	def amountEuro(self):
		return self.amount / float(100)

	def __str__(self):
		return "Communism by {}\nAmount: {}€\nReason: {}\nCommunists: {}\n" \
			.format(self.creator['name'], self.amountEuro(), self.reason, userListToString(self.members))

def communism(bot, update):
	amount, reason = parseArgs(update.message, [ARG_AMOUNT, ARG_REST], "\nUsage: /communism <amount> <reason ...>")

	sender = getOrCreateUser(update.message.from_user)
	id = str(sender['id'])

	if id in communisms:
		update.message.reply_text("You already have a communism in progress")
		return

	communism = Communism(sender, amount, reason)
	communism.message = update.message.reply_text(str(communism), reply_markup=communism.message_markup)
	communisms[id] = communism

def communismQuery(bot, update):
	sender = getOrCreateUser(update.callback_query.from_user)
	split = update.callback_query.data.split(" ")

	if len(split) != 3:
		print(split)
		raise Exception("invalid callback query")
	elif split[1] not in communisms:
		raise Exception("invalid ID")

	communism = communisms[split[1]]
	members = communism.members
	isAdmin = sender == communism.creator

	if split[2] == "join/leave":
		if sender in members:
			members.remove(sender)
		else:
			members.append(sender)

		if len(members) == 0:
			del communisms[split[1]]
			communism.message.edit_text("Everyone left, the communism died")
		else:
			communism.message.edit_text(str(communism), reply_markup=communism.message_markup)
	elif isAdmin and split[2] == "ok":
		count = len(members)
		amount = communism.amount // count

		# if the amount can't be split equally eveyone pays 1 cent more
		if communism.amount % count != 0:
			amount = amount + 1

		reason = "communism by " + communism.creator['nick']
		for member in members:
			createTransaction(member, -amount, reason)

		createTransaction(communism.creator, communism.amount, reason)
		del communisms[split[1]]

		creator = communism.creator['name']
		text = "Communism by {}\n{} paid {}\n{} received {}\nDescription: {}" \
			.format(creator, userListToString(self.members), amount / float(100),
			creator, communism.amountEuro(), communism.reason)
		communism.message.edit_text(text)

	elif isAdmin and split[2] == "cancel":
		del communisms[split[1]]
		communism.message.edit_text("Communism canceled")

class Pay:
	def __init__(self, creator, amount, reason):
		self.creator = creator
		self.amount = amount
		self.reason = reason
		self.approved = []
		self.disapproved = []
		self.message = None

		prefix = "pay " + str(creator['id'])
		self.message_markup = telegram.InlineKeyboardMarkup([
			[
				telegram.InlineKeyboardButton("APPROVE", callback_data=prefix + " approve"),
			],
			[
				telegram.InlineKeyboardButton("DISAPPROVE", callback_data=prefix + " disapprove"),
			],
		])

	def amountEuro(self):
		return self.amount / float(100)

	def __str__(self):
		return "Pay by {}\nAmount: {}€\nReason: {}\nApprovers: {}\nDisapprovers: {}\n" \
			.format(self.creator['name'], self.amountEuro(), self.reason,
			userListToString(self.approved), userListToString(self.disapproved))

def pay(bot, update):
	amount, reason = parseArgs(update.message, [ARG_AMOUNT, ARG_REST], "\nUsage: /pay <amount> <reason ...>")

	sender = getOrCreateUser(update.message.from_user)
	id = str(sender['id'])

	if id in pays:
		update.message.reply_text("You already have a pay in progress")
		return

	pay = Pay(sender, amount, reason)
	pay.message = update.message.reply_text(str(pay), reply_markup=pay.message_markup)
	pays[id] = pay

def payQuery(bot, update):
	sender = getOrCreateUser(update.callback_query.from_user)
	split = update.callback_query.data.split(" ")

	if len(split) != 3:
		print(split)
		raise Exception("invalid callback query")
	elif split[1] not in pays:
		raise Exception("invalid ID")

	pay = pays[split[1]]
	approved = pay.approved
	disapproved = pay.disapproved
	changed = False
	#isAdmin = sender == pay.creator

	if sender == pay.creator:
		if split[2] == "disapprove":
			del pays[split[1]]
			pay.message.edit_text("Pay canceled (the creator disapproves himself).")
			return
	elif split[2] == "approve":
		if sender not in approved:
			approved.append(sender)
			changed = True
		if sender in disapproved:
			disapproved.remove(sender)
	elif split[2] == "disapprove":
		if sender in approved:
			approved.remove(sender)
		if sender not in disapproved:
			disapproved.append(sender)
			changed = True

	def checkList(users):
		if len(users) < config['pay-min-users']:
			return False

		hasAdmin = False
		for user in users:
			if user['id'] in config['admins']:
				hasAdmin = True
				break

		return hasAdmin

	if checkList(pay.disapproved):
		del pays[split[1]]
		pay.message.edit_text("DISAPPROVED\n" + str(pay))
	elif checkList(pay.approved):
		del pays[split[1]]
		createTransaction(pay.creator, pay.amount, "pay for {}, approved by {}" \
			.format(pay.reason, userListToString(pay.approved)))
		pay.message.edit_text("APPROVED\n" + str(pay))
	elif changed:
		pay.message.edit_text(str(pay), reply_markup=pay.message_markup)
	else:
		update.callback_query.answer()



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
updater.dispatcher.add_handler(CommandHandler("communism", tryWrap(communism)))
updater.dispatcher.add_handler(CommandHandler("pay", tryWrap(pay)))

updater.dispatcher.add_handler(CallbackQueryHandler(tryWrap(communismQuery), pattern="^communism"))
updater.dispatcher.add_handler(CallbackQueryHandler(tryWrap(payQuery), pattern="^pay"))

updater.start_polling()
updater.idle()
