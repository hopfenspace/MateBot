from typing import Any

import telegram


class MateBotUser:
    """
    This class represents a MateBot's user and stores his balance.

    :param user: The Telegram user to create a MateBotUser for
    :type user: telegram.User
    """

    def __init__(self, user: telegram.User):
        self.id = user.id
        """The user's id"""
        self.name = user.full_name
        """The user's name"""
        self.nick = user.username
        """The user's nickname or username"""
        self.balance = 0
        """The user's balance is an amount of money in cent. Positive values mean the bot ows the user."""

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
