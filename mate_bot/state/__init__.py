#!/usr/bin/env python3

from typing import Union

from .user import MateBotUser, CommunityUser
from .transactions import Transaction, TransactionLog



users = load("state.json")
logFd = open("transactions.log", "a")




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
