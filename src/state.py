import json, datetime
from config import config

with open("state.json", "r") as fd:
	users = json.load(fd)

logFd = open("transactions.log", "a")

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

	userState = users[id]

	if user.username != userState['nick']:
		userState['nick'] = user.username
		saveState()
	if user.full_name != userState['name']:
		userState['name'] = user.full_name
		saveState()

	return userState

def findUserByNick(nick):
	for id in users:
		user = users[id]
		if user['nick'] == nick:
			return user

	return None

def userListToString(users):
	names = []
	for member in users:
		names.append(member['name'])

	return ", ".join(names)
