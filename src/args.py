from config import config
from state import getOrCreateUser, findUserByNick

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
