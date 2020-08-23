#!/usr/bin/env python3

import datetime
import telegram


class MateBotUser:
    """
    MateBotUser convenience class storing all information about a user

    Specify a Telegram User object to initialize this object. It will
    fetch all available data from the database in the background.
    Do not cache these values for consistency reasons.
    """

    def __init__(self, user: telegram.User):
        """
        :param user: the Telegram user to create a MateBot user for
        :type user: telegram.User
        """

        self._user = user

    def __eq__(self, other) -> bool:
        if isinstance(other, type(self)):
            return self.uid == other.uid and self.tid == other.tid
        return False

    @property
    def user(self) -> telegram.User:
        return self._user

    @property
    def uid(self) -> int:
        return self._id

    @property
    def tid(self) -> int:
        return self._user.id

    @property
    def username(self) -> str:
        return self._user.username

    @property
    def name(self) -> str:
        return self._user.full_name

    @property
    def balance(self) -> int:
        return self._balance

    @property
    def permission(self) -> bool:
        return self._permission

    @property
    def created(self) -> datetime.datetime:
        return self._created

    @property
    def accessed(self) -> datetime.datetime:
        return self._accessed
