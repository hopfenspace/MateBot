"""
MateBot helper methods to find users, names or usernames
"""

import typing

from mate_bot.state import user
from mate_bot.state.dbhelper import execute as _execute


def find_user_by_name(name: str, matching: bool = False) -> typing.Optional[user.MateBotUser]:
    """
    Find a MateBotUser by his name

    Note that this function will always try to return exactly one result.
    If there are multiple records in the database, all matching the pattern,
    then this function will return None. If it's okay for you to get a list of
    possible names, then you may look into `find_names_by_pattern`.

    :param name: the user's name on Telegram
    :type name: str
    :param matching: switch if pattern matching should be enabled
    :type matching: bool
    :return: MateBotUser or None
    """

    if matching:
        if not name.startswith("%"):
            name = "%" + name
        if not name.endswith("%"):
            name += "%"
        rows, values = _execute(
            "SELECT * FROM users WHERE name LIKE %s",
            (name,)
        )

    else:
        rows, values = _execute(
            "SELECT * FROM users WHERE name=%s",
            (name,)
        )

    if rows != 1 or len(values) != 1:
        return None

    return user.MateBotUser(values[0]["id"])


def find_user_by_username(
        username: str,
        matching: bool = False
) -> typing.Optional[user.MateBotUser]:
    """
    Find a MateBotUser by his username

    Note that this function will always try to return exactly one result.
    If there are multiple records in the database, all matching the pattern,
    then this function will return None. If it's okay for you to get a list of
    possible usernames, then you may look into `find_usernames_by_pattern`.

    :param username: the user's username on Telegram
    :type username: str
    :param matching: switch if pattern matching should be enabled
    :type matching: bool
    :return: MateBotUser or None
    """

    if username.startswith("@"):
        username = username[1:]

    if matching:
        if not username.startswith("%"):
            username = "%" + username
        if not username.endswith("%"):
            username += "%"
        rows, values = _execute(
            "SELECT * FROM users WHERE username LIKE %s",
            (username,)
        )

    else:
        rows, values = _execute(
            "SELECT * FROM users WHERE username=%s",
            (username,)
        )

    if rows != 1 or len(values) != 1:
        return None

    return user.MateBotUser(values[0]["id"])


def find_names_by_pattern(pattern: str) -> typing.List[str]:
    """
    Find users' names that match the specified pattern

    :param pattern: pattern to search for in the database records
    :type pattern: str
    :return: list of strings
    """

    if not pattern.startswith("%"):
        pattern = "%" + pattern
    if not pattern.endswith("%"):
        pattern += "%"

    results = []
    for values in _execute("SELECT name FROM users WHERE name LIKE %s", (pattern,))[1]:
        results.append(values["name"])
    return results


def find_usernames_by_pattern(pattern: str) -> typing.List[str]:
    """
    Find usernames that match the specified pattern

    :param pattern: pattern to search for in the database records
    :type pattern: str
    :return: list of strings
    """

    if not pattern.startswith("%"):
        pattern = "%" + pattern
    if not pattern.endswith("%"):
        pattern += "%"

    results = []
    for values in _execute("SELECT username FROM users WHERE username LIKE %s", (pattern,))[1]:
        results.append(values["username"])
    return results
