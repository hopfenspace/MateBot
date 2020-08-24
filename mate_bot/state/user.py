#!/usr/bin/env python3

import typing
import datetime
import telegram
import collections

from .dbhelper import execute as _execute


class BaseBotUser:
    """
    Base class for MateBot users
    """

    _user = None
    _id = 0
    _name = ""
    _username = ""
    _balance = 0
    _permission = 0
    _created = datetime.datetime.fromtimestamp(0)
    _accessed = datetime.datetime.fromtimestamp(0)

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, type(self)):
            return self.uid == other.uid and self.tid == other.tid
        return False

    def _get_remote_record(self, use_tid: bool = True) -> typing.Tuple[int, typing.List[typing.Dict[str, typing.Any]]]:
        """
        Retrieve the remote record for the current user (internal use only!)

        :param use_tid: switch whether to use Telegram ID (True) or internal database ID (False)
        :type use_tid: boolean
        :return: number of affected rows and fetched data record
        """

        if use_tid:
            return _execute("SELECT * FROM users WHERE tid=%s", (self._user.id,))
        else:
            return _execute("SELECT * FROM users WHERE id=%s", (self._id,))

    def _unpack_record(self, record: typing.Dict[str, typing.Any]) -> None:
        """
        Unpack a database record dict to overwrite the internal attributes (internal use only!)

        :param record: database record as returned by a `SELECT * FROM users` query
        :type record: dict
        :return: None
        """

        self._id = record["id"]
        self._name = record["name"]
        self._username = record["username"]
        self._balance = record["balance"]
        self._permission = record["permission"]
        self._created = record["tscreated"]
        self._accessed = record["tsaccessed"]

    def _update_record(self, column: str, value: typing.Union[str, int, bool]) -> typing.Union[str, int]:
        """
        Update a value in the column of the current user record in the database

        :param column: name of the database column
        :type column: str
        :param value: value to be set for the current user in the specified column
        :type value: str, int or bool
        :return: str or int
        """

        if isinstance(value, str):
            value = "'{}'".format(value)
        if isinstance(value, float):
            if value.is_integer():
                value = int(value)
            else:
                raise TypeError("No floats allowed")
        if not isinstance(value, (bool, int)):
            raise TypeError("Unsupported type")

        if column not in ["username", "name", "balance", "permission"]:
            raise RuntimeError("Operation not allowed")

        _execute(
            "UPDATE users SET %s=%s WHERE tid=%s",
            (column, value, self._user.id)
        )

        state, result = _execute(
            "SELECT %s, tsaccessed FROM users WHERE tid=%s",
            (column, self._user.id)
        )
        self._accessed = result[0]["tsaccessed"]
        return result[0][column]

    def _update_local(self, record: typing.Dict[str, typing.Any]) -> None:
        """
        Apply a database record to the local copy and check for consistency with Telegram

        :param record: database record as returned by a `SELECT * FROM users` query
        :type record: dict
        :return: None
        """

        self._unpack_record(record)

        if self._name != self._user.full_name:
            self._name = self._update_record("name", self._user.full_name)

        if self._username != self._user.name:
            self._username = self._update_record("username", self._user.name)

    def update(self) -> None:
        """
        Re-read the internal values from the database

        :return: None
        """

        state, values = self._get_remote_record()

        if state == 1 and len(values) == 1:
            self._update_local(values[0])

    @property
    def uid(self) -> int:
        return self._id

    @property
    def tid(self) -> int:
        return self._user.id

    @property
    def username(self) -> str:
        return self._username

    @property
    def name(self) -> str:
        return self._name

    @property
    def balance(self) -> int:
        return self._balance

    @property
    def permission(self) -> bool:
        return bool(self._permission)

    @property
    def created(self) -> datetime.datetime:
        return self._created

    @property
    def accessed(self) -> datetime.datetime:
        return self._accessed


class CommunityUser(BaseBotUser):
    """
    Special user which receives consume transactions and sends payment transactions
    """

    def __init__(self, uid: int):
        """
        :param uid: ID of the user's record in the database
        :type uid: int
        :raises RuntimeError: when no user with the specified ID was found
        """

        User = collections.namedtuple("User", ["id", "name", "username", "full_name"])

        self._id = uid
        state, values = self._get_remote_record(False)

        if state == 0 or len(values) == 0:
            raise RuntimeError(
                "No community user created for ID {} yet! Do this manually and try again.".format(uid)
            )

        elif state == 1 and len(values) == 1:
            self._unpack_record(values[0])
            self._user = User(
                values[0]["tid"],
                self._name,
                self._username,
                self._name
            )

    @property
    def user(self) -> None:
        return None


class MateBotUser(BaseBotUser):
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

        state, values = self._get_remote_record()

        if state == 0 and len(values) == 0:
            _execute(
                "INSERT INTO users (tid, username, name) VALUES (%s, %s, %s)",
                (self._user.id, self._user.name, self._user.full_name)
            )

            state, values = self._get_remote_record()

        if state == 1 and len(values) == 1:
            self._update_local(values[0])

    @property
    def user(self) -> telegram.User:
        return self._user

    @property
    def permission(self) -> bool:
        return bool(self._permission)

    @permission.setter
    def permission(self, new: bool):
        self._permission = self._update_record("permission", bool(new))
