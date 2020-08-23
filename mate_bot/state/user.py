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

        def _update_record(column: str, value: str) -> str:
            if not isinstance(value, str):
                raise TypeError("expected str")

            _execute("UPDATE users SET {}='{}' WHERE tid={}".format(
                column,
                value,
                self._user.id
            ))

            _, result = _execute("SELECT {}, tsaccessed FROM users WHERE tid={}".format(
                column,
                self._user.id
            ))
            self._accessed = result[0]["tsaccessed"]
            return result[0][column]

        self._user = user

        state, values = _execute("SELECT * FROM users WHERE tid={}".format(self._user.id))

        if state == 1 and len(values) == 1:
            record = values[0]
            self._id = record["id"]
            self._name = record["name"]
            self._username = record["username"]
            self._balance = record["balance"]
            self._permission = record["permission"]
            self._created = record["tscreated"]
            self._accessed = record["tsaccessed"]

            if self._name != self._user.full_name:
                self._name = _update_record("name", self._user.full_name)

            if self._username != self._user.username:
                self._username = _update_record("username", self._user.username)


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
