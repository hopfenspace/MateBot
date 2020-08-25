#!/usr/bin/env python3

import typing
import telegram

from . import user
from .dbhelper import execute as _execute


def find_user_by_username(username: str) -> typing.Optional[user.MateBotUser]:
    """
    Find a MateBotUser by his username

    Note that this function will always try to return exactly one result.
    If there are multiple records in the database, all matching the pattern,
    then this function will return None. If it's okay for you to get a list of
    possible usernames, then you may look into `find_usernames_by_pattern`.

    :param username: the user's username on Telegram
    :type username: str
    :return: MateBotUser or None
    """

    if username.startswith("@"):
        username = username[1:]
    username = "%" + username + "%"

    rows, values = _execute(
        "SELECT * FROM users WHERE username LIKE %s",
        (username,)
    )

    if rows != 1 or len(values) != 1:
        return None

    last_name = None
    if values[0]["name"].count(" ") > 0:
        last_name = values[0]["name"].split(" ")[1:]
    username = None
    if values[0]["username"]:
        if values[0]["username"].startswith("@"):
            username = values[0]["username"][1:]
        else:
            username = values[0]["username"]

    return user.MateBotUser(telegram.User(
        values[0]["tid"],
        values[0]["name"].split(" ")[0],
        False,
        last_name,
        username
    ))
