import telegram
from config import config
from state import getOrCreateUser, createTransaction, userListToString
from args import parseArgs, ARG_AMOUNT, ARG_REST

pays = {}

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
	amount, reason = parseArgs(update.message,
		[ARG_AMOUNT, ARG_REST],
		[None, ""],
		"\nUsage: /pay <amount> [reason ...]"
	)

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
		print(split)
		raise Exception("invalid ID")

	pay = pays[split[1]]
	approved = pay.approved
	disapproved = pay.disapproved
	changed = False

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
