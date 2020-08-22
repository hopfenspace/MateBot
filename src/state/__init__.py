import datetime
import json
from typing import List, Union

import telegram

from .user import MateBotUser
from .io import load, save


users = load("state.json")
logFd = open("transactions.log", "a")


def save_state():
    save(users, "state.json")


def create_transaction(user: MateBotUser, diff: int, reason: str) -> None:
    """
    Change a user's balance and log this change.

    :param user: The user whose balance is to be changed
    :type user: MateBotUser
    :param diff: Amount to change the ``user``'s balance by in cent
        positive values mean gain, negative values mean loss for the ``user``
    :type diff: int
    :param reason: A reason to make the log easier to understand
    :type reason: str
    """
    log = {
        'timestamp': datetime.datetime.now().timestamp(),
        'user': user.id,
        'diff': diff,
        'reason': reason
    }
    logFd.write(json.dumps(log) + '\n')
    logFd.flush()

    user.balance += diff
    save_state()


def get_or_create_user(user: telegram.User) -> MateBotUser:
    """
    Convert telegram's user representation into ours.

    Use telegram's user id too look up our user object.
    If there isn't one, create it.

    :param user: A Telegram user
    :type user: telegram.User
    :return: A MateBot user
    :rtype: MateBotUser
    """
    user_id = str(user.id)
    if user_id not in users:
        users[user_id] = MateBotUser(user)
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


def find_user_by_nick(nick: str) -> Union[MateBotUser, None]:
    """
    Find a user by his nickname.

    :param nick: A user's nickname on Telegram
    :type nick: str
    :return: The user or ``None``
    :rtype: MateBotUser or None
    """
    for user_id in users:
        user = users[user_id]
        if user.nick == nick:
            return user
    else:
        return None
