#!/usr/bin/env python3

from typing import List, Dict, Any, Tuple
import telegram

from state import BaseBotUser, get_or_create_user


def user_list_to_string(user_list: List[BaseBotUser]) -> str:
    """
    Convert a list of users into a string.

    :param user_list: List of users
    :type user_list: List[BaseBotUser]
    :return: String representation of the list
    :rtype: str
    """

    return ", ".join(map(lambda x: x.name, user_list))


def get_data_from_query(update: telegram.Update, objects: Dict[str, Any]) -> Tuple[BaseBotUser, Any, str, str, str]:
    """
    Get the sender, the object the query is meant for and the split message

    This was a duplicate peace of code in pay's and communism's query

    :param update: The query's update object
    :type update: telegram.Update
    :param objects: Of which to find the object the query is for
    :type objects: Dict[Any]
    :return: sender, object, cmd, sender_id, action
    :rtype: Tuple[BaseBotUser, Any, List[str]]
    """

    sender = get_or_create_user(update.callback_query.from_user)
    split = update.callback_query.data.split(" ")

    if len(split) != 3:
        print(split)
        raise Exception("invalid callback query")
    elif split[1] not in objects:
        print(split)
        raise Exception("invalid ID")

    return sender, objects[split[1]], split[1], split[2], split[3]
