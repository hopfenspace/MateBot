import re
from typing import List, Any

from config import config
from state import get_or_create_user, find_user_by_nick


def parseAmount(text: str, min_amount: int = 0, max_amount: int = config["max-amount"]) -> int:
	"""
	Take a string representation of an amount of money and return the amount as a integer in cent.

	:param text: string representing an amount like "0,10" for 10 cents
	:param min_amount: The minimum valid amount (in cent)
	:param max_amount: The maximum valid amount (in cent)
	:return: Money amount (in cent)
	"""
	match = re.match("^(\d+)([,.](\d+))?$", text)
	if not match:
		return None, "not a positive number"
	val = int(match.group(1)) * 100

    if match.group(3):
        if len(match.group(3)) > 2:
            return None, "too precise ({} only two decimals are supported)".format(match.group(0))
        elif len(match.group(3)) == 1:
            val += int(match.group(3)) * 10
        else:
            val += int(match.group(3))

    # TODO make use of min
	if val == 0:
        return None, "zero"
    elif val > max_amount * 100:
        return None, "larger than the maximum allowed amount"

    return val, None


ARG_TEXT = 0
ARG_INT = 1
ARG_AMOUNT = 2
ARG_USER = 3
ARG_REST = 4


def parseArgs(msg: str, arg_types: List[int], defaults: List[Any], usage: str = "") -> List[Any]:
	"""
	Parse a message string for arguments contained.

	:param msg: the incoming message as string
	:param arg_types: a list of constants defining which type of argument should be at its position
	:param defaults: a list of values to use if the msg is shorter than arg_types might expect
	:param usage: a string appended to error messages
	:return: a list of values contained in the msg
	"""
	split = msg.text.split(" ")
	result = []
	error = None

	offset = len(split[0]) + 1
	split = split[1 : ]

	for i, expected in enumerate(arg_types):
		if i < len(split):
			arg = split[i]
		elif i < len(defaults) and defaults[i] is not None:
			result.append(defaults[i])
			continue
		else:
			error = "Argument {} not specified".format(i)
			break

		if expected == ARG_TEXT:
			result.append(arg)
		elif expected == ARG_INT:
			try:
				val = int(arg)
				result.append(val)
			except:
				error = "Argument {} should be an int but is '{}'".format(i, arg)
				break
		elif expected == ARG_AMOUNT:
			val, error = parseAmount(arg)
			if val is None:
				error = "Argument {} should be an amount but is {}".format(i, error)
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
