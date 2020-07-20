import datetime
import json

with open("state.json", "r") as fd:
    users = json.load(fd)

logFd = open("transactions.log", "a")


def save_state():
    with open("state.json", "w") as fd:
        json.dump(users, fd)


def create_transaction(user, diff, reason):
    log = {
        'timestamp': datetime.datetime.now().timestamp(),
        'user': user["id"],
        'diff': diff,
        'reason': reason
    }
    logFd.write(json.dumps(log) + '\n')
    logFd.flush()

    user['balance'] += diff
    save_state()


def get_or_create_user(user):
    user_id = str(user.id)
    if user_id not in users:
        users[user_id] = {
            'id': user.id,
            'name': user.full_name,
            'nick': user.username,
            'balance': 0
        }
        save_state()

    user_state = users[user_id]

    if user.username != user_state['nick']:
        user_state['nick'] = user.username
        save_state()
    if user.full_name != user_state['name']:
        user_state['name'] = user.full_name
        save_state()

    return user_state


def find_user_by_nick(nick):
    for user_id in users:
        user = users[user_id]
        if user['nick'] == nick:
            return user

    return None


def user_list_to_string(user):
    names = []
    for member in user:
        names.append(member['name'])

    return ", ".join(names)
