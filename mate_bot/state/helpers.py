#!/usr/bin/env python3

import typing
import telegram

from . import user
from .dbhelper import execute as _execute


def _create_user_from_record(record: typing.Dict[str, typing.Union[str, int]]) -> user.MateBotUser:
    """
    Create a MateBotUser object based on a record of the database

    :param record: database record containing all necessary information
    :type record: dict
    :return: MateBotUser object
    """

    last_name = None
    if record["name"].count(" ") > 0:
        last_name = record["name"].split(" ")[1:]
    username = None
    if record["username"]:
        if record["username"].startswith("@"):
            username = record["username"][1:]
        else:
            username = record["username"]

    return user.MateBotUser(telegram.User(
        record["tid"],
        record["name"].split(" ")[0],
        False,
        last_name,
        username
    ))


def find_user_by_name(name: str, matching: bool = True) -> typing.Optional[user.MateBotUser]:
    """
    Find a MateBotUser by his name

    Note that this function will always try to return exactly one result.
    If there are multiple records in the database, all matching the pattern,
    then this function will return None. If it's okay for you to get a list of
    possible names, then you may look into `find_names_by_pattern`.

    :param name: the user's username on Telegram
    :type name: str
    :param matching: switch if pattern matching should be enabled
    :type matching: bool
    :return: MateBotUser or None
    """

    if matching:
        name = "%" + name + "%"

    rows, values = _execute(
        "SELECT * FROM users WHERE username LIKE %s",
        (name,)
    )

    if rows != 1 or len(values) != 1:
        return None

    return create_user_from_record(values[0])


def find_user_by_username(username: str, matching: bool = True) -> typing.Optional[user.MateBotUser]:
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
        username = "%" + username + "%"

    rows, values = _execute(
        "SELECT * FROM users WHERE username LIKE %s",
        (username,)
    )

    if rows != 1 or len(values) != 1:
        return None

    return create_user_from_record(values[0])


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
    for v in _execute("SELECT name FROM users WHERE name LIKE %s", (pattern,))[1]:
        results.append(v["name"])
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
    for v in _execute("SELECT username FROM users WHERE username LIKE %s", (pattern,))[1]:
        results.append(v["username"])
    return results

