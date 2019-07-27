import telegram
from state import getOrCreateUser, createTransaction, userListToString
from args import parseArgs, ARG_AMOUNT, ARG_REST

communisms = {}

class Communism:
	def __init__(self, creator, amount, reason):
		self.creator = creator
		self.amount = amount
		self.reason = reason
		self.members = [creator]
		self.message = None
		self.externs = 0

		prefix = "communism " + str(creator['id'])
		self.message_markup = telegram.InlineKeyboardMarkup([
			[
				telegram.InlineKeyboardButton("JOIN/LEAVE", callback_data=prefix + " join/leave"),
			],
			[
				telegram.InlineKeyboardButton("EXTERN -", callback_data=prefix + " extern-"),
				telegram.InlineKeyboardButton("EXTERN +", callback_data=prefix + " extern+"),
			],
			[
				telegram.InlineKeyboardButton("OK", callback_data=prefix + " ok"),
				telegram.InlineKeyboardButton("CANCEL", callback_data=prefix + " cancel"),
			],
		])

	def amountEuro(self):
		return self.amount / float(100)

	def updateText(self):
		self.message.edit_text(str(self), reply_markup=self.message_markup)

	def __str__(self):
		return "Communism by {}\nAmount: {}€\nReason: {}\nExterns: {}\nCommunists: {}\n" \
			.format(self.creator['name'], self.amountEuro(), self.reason, self.externs, userListToString(self.members))

def communism(bot, update):
	amount, reason = parseArgs(update.message,
		[ARG_AMOUNT, ARG_REST],
		[None, ""],
		"\nUsage: /communism <amount> [reason ...]"
	)

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
		print(split)
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
			communism.updateText()
	elif isAdmin and split[2] == "ok":
		count = len(members) + communism.externs
		amount = communism.amount // count

		# if the amount can't be split equally eveyone pays 1 cent more
		if communism.amount % count != 0:
			amount = amount + 1

		reason = "communism by " + communism.creator['name']
		for member in members:
			createTransaction(member, -amount, reason)

		payout = communism.amount - communism.externs * amount
		createTransaction(communism.creator, payout, reason)
		del communisms[split[1]]

		creator = communism.creator['name']
		amountf = amount / float(100)
		text = "Communism by {}\n{} paid {}\n{} received {}\n{} has to be collected from {} externs\nDescription: {}" \
			.format(creator, userListToString(communism.members), amountf,
			creator, payout / float(100), amountf, communism.externs, communism.reason)
		communism.message.edit_text(text)

	elif isAdmin and split[2] == "cancel":
		del communisms[split[1]]
		communism.message.edit_text("Communism canceled")

	elif isAdmin and split[2] == "extern-":
		if communism.externs > 0:
			communism.externs -= 1
			communism.updateText()
		else:
			update.message.reply_text("Cannot reduce externs below zero")

	elif isAdmin and split[2] == "extern+":
		communism.externs += 1
		communism.updateText()
