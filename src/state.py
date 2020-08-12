import datetime
import json
from typing import List, Dict, Union

from telegram import User


with open("state.json", "r") as fd:
    users = json.load(fd)

logFd = open("transactions.log", "a")


def save_state():
    with open("state.json", "w") as fd:
        json.dump(users, fd)


def create_transaction(user: Dict, diff: int, reason: str) -> None:
    """
    Change a user's balance and log this change.

    :param user: The user whose balance is to be changed
    :type user: Dict
    :param diff: Amount to change the ``user``'s balance by in cent
        positive values mean gain, negative values mean loss for the ``user``
    :type diff: int
    :param reason: A reason to make the log easier to understand
    :type reason: str
    """
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


def get_or_create_user(user: User) -> Dict:
    """
    Convert telegram's user representation into ours.

    Use telegram's user id too look up our dict representation.
    If there isn't any, create one.

    :param user: A telegram user
    :type user: User
    :return: A MateBot user
    :rtype: Dict
    """
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

    # Update user's nickname or name if he changed it on telegram.
    if user.username != user_state['nick']:
        user_state['nick'] = user.username
        save_state()
    if user.full_name != user_state['name']:
        user_state['name'] = user.full_name
        save_state()

    return user_state


def find_user_by_nick(nick: str) -> Union[Dict, None]:
    """
    Find a user by his nickname.

    :param nick: A user's nickname on telegram
    :type nick: str
    :return: The user or ``None``
    :rtype: Dict or None
    """
    for user_id in users:
        user = users[user_id]
        if user['nick'] == nick:
            return user
    else:
        return None


def user_list_to_string(user_list: List[Dict]) -> str:
    """
    Convert a list of users into a string.

    :param user_list: List of users
    :type user_list: List[Dict]
    :return: String representation of the list
    :rtype: str
    """
    return ", ".join(map(lambda x: x["names"], user_list))
