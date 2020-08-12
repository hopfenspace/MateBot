import re
from typing import List, Any
from telegram import Message

from config import config
from state import get_or_create_user, find_user_by_nick


class ParsingError(Exception):
	pass


def parseAmount(text: str, min_amount: int = 0, max_amount: int = config["max-amount"]) -> int:
	"""
	Take a string representation of an amount of money and return the amount as a integer in cent.

	:param text: string representing an amount like "0,10" for 10 cents
	:param min_amount: The minimum valid amount (in cent)
	:param max_amount: The maximum valid amount (in cent)
	:raises ParsingError:
	:return: Money amount (in cent)
	"""
	match = re.match("^(\d+)([,.](\d+))?$", text)
	if match is None:
		raise ParsingError("not a positive number")

	val = int(match.group(1)) * 100
	if match.group(3):
		if len(match.group(3)) > 2:
			raise ParsingError("too precise ({} only two decimals are supported)".format(match.group(0)))
		elif len(match.group(3)) == 1:
			val += int(match.group(3)) * 10
		else:
			val += int(match.group(3))

	# TODO make use of min
	if val == 0:
		raise ParsingError("zero")
	elif val > max_amount * 100:
		raise ParsingError("larger than the maximum allowed amount")

	return val


ARG_TEXT = 0
ARG_INT = 1
ARG_AMOUNT = 2
ARG_USER = 3
ARG_REST = 4


def parseArgs(msg: Message, arg_types: List[int], defaults: List[Any], usage: str = "") -> List[Any]:
	"""
	Parse a message string for arguments contained.

	If an error occurs, its error message will be replied back to the msg and raised.

	:param msg: the incoming message
	:param arg_types: a list of constants defining which type of argument should be at its position
	:param defaults: a list of values to use if the msg is shorter than arg_types might expect
	:param usage: a string appended to error messages
	:raises Exception:
	:return: a list of values contained in the msg
	"""
	try:
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
				raise ParsingError("Argument {} not specified".format(i))

			if expected == ARG_TEXT:
				result.append(arg)
			elif expected == ARG_INT:
				try:
					result.append(int(arg))
				except ValueError:
					raise ParsingError("Argument {} should be an int but is '{}'".format(i, arg))
			elif expected == ARG_AMOUNT:
				try:
					result.append(parseAmount(arg))
				except ParsingError as e:
					raise ParsingError("Argument {} should be an amount but is {}".format(i, str(e)))
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
					raise ParsingError("Argument {} should be an user but is '{}'".format(i, arg))

				result.append(user)
			elif expected == ARG_REST:
				result.append(" ".join(split[i:]))
				break

			offset = offset + len(arg) + 1

		return result

	except ParsingError as e:
		error = str(e) + usage
		msg.reply_text(error)
		raise Exception(error)
