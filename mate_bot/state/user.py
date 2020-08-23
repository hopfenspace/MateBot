#!/usr/bin/env python3

from typing import Any

import telegram


class MateBotUser:
    """
    This class represents a MateBot's user and stores his balance.

    :param user: The Telegram user to create a MateBotUser for
    :type user: telegram.User
    """

    def __init__(self, user: telegram.User = None, id: int = 0, name: str = "", nick: str = "", balance: int = 0):
        self.id = id
        """The user's id"""
        self.name = name
        """The user's name"""
        self.nick = nick
        """The user's nickname or username"""
        self.balance = balance
        """The user's balance is an amount of money in cent. Positive values mean the bot ows the user."""

        # Update self using the telegram.User
        if user is not None:
            self.id = user.id
            self.name = user.full_name
            self.nick = user.username

    def __getitem__(self, key: str) -> Any:
        """
        Legacy function. Users used to be dicts.

        :param key:
        :type key: str
        :return:
        :rtype: Any
        """

        return self.__getattribute__(key)

    def __setitem__(self, key: str, value: Any) -> None:
        """
        Legacy function. Users used to be dicts.

        :param key:
        :type key: str
        :param value:
        :type value: Any
        """

        self.__setattr__(key, value)
