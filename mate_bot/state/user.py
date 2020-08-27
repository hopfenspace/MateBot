#!/usr/bin/env python3

import typing
import pymysql.err as _err
import datetime as _datetime
import telegram as _telegram

from .dbhelper import execute as _execute, EXECUTE_TYPE as _EXECUTE_TYPE


class BaseBotUser:
    """
    Base class for MateBot users
    """

    _user = None
    _id = 0
    _tid = None
    _name = ""
    _username = ""
    _balance = 0
    _permission = 0
    _active = False
    _external = False
    _created = _datetime.datetime.fromtimestamp(0)
    _accessed = _datetime.datetime.fromtimestamp(0)

    _ALLOWED_UPDATES = []

    @classmethod
    def get_uid_from_tid(cls, tid: int) -> typing.Optional[int]:
        """
        Retrieve the user ID from the database using the Telegram ID as selector

        :param tid: Telegram user ID
        :type tid: int
        :return: int or None
        """

        s, v = _execute("SELECT id FROM users WHERE tid=%s", (tid,))
        if s == 1 and len(v) == 1:
            return v[0]["id"]
        return None

    @classmethod
    def get_tid_from_uid(cls, uid: int) -> typing.Optional[int]:
        """
        Retrieve the Telegram ID from the database using the user ID as selector

        :param uid: internal user ID
        :type uid: int
        :return: int or None
        """

        s, v = _execute("SELECT tid FROM users WHERE id=%s", (uid,))
        if s == 1 and len(v) == 1:
            return v[0]["tid"]
        return None

    @classmethod
    def get_name_from_uid(cls, uid: int) -> typing.Optional[str]:
        """
        Retrieve the stored name for the given user ID

        :param uid: internal user ID
        :type uid: int
        :return: str or None
        """

        s, v = _execute("SELECT name FROM users WHERE id=%s", (uid,))
        if s == 1 and len(v) == 1:
            return v[0]["name"]
        return None

    @classmethod
    def get_username_from_uid(cls, uid: int) -> typing.Optional[str]:
        """
        Retrieve the stored username for the given user ID

        :param uid:
        :return:
        """

        s, v = _execute("SELECT username FROM users WHERE id=%s", (uid,))
        if s == 1 and len(v) == 1:
            return v[0]["username"]
        return None

    def __eq__(self, other: typing.Any) -> bool:
        if isinstance(other, type(self)):
            return self.uid == other.uid and self.tid == other.tid
        return False

    def _get_remote_record(self, use_tid: bool = True) -> _EXECUTE_TYPE:
        """
        Retrieve the remote record for the current user (internal use only!)

        :param use_tid: switch whether to use Telegram ID (True) or internal database ID (False)
        :type use_tid: bool
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
        self._tid = record["tid"]
        self._name = record["name"]
        self._username = record["username"]
        self._balance = record["balance"]
        self._permission = record["permission"]
        self._active = record["active"]
        self._created = record["created"]
        self._accessed = record["accessed"]

    def _update_record(self, column: str, value: typing.Union[str, int, bool, None]) -> typing.Union[str, int]:
        """
        Update a value in the column of the current user record in the database

        :param column: name of the database column
        :type column: str
        :param value: value to be set for the current user in the specified column
        :type value: str, int, bool or None
        :return: str or int
        :raises TypeError: invalid type for value found
        :raises RuntimeError: when the column is not marked writeable by configuration
        """

        if isinstance(value, float):
            if value.is_integer():
                value = int(value)
            else:
                raise TypeError("No floats allowed")
        if value is not None:
            if not isinstance(value, (str, int, bool)):
                raise TypeError("Unsupported type")

        if column not in self._ALLOWED_UPDATES:
            raise RuntimeError("Operation not allowed")

        _execute(
            "UPDATE users SET {}=%s WHERE tid=%s".format(column),
            (value, self._user.id)
        )

        state, result = _execute(
            "SELECT %s, accessed FROM users WHERE tid=%s",
            (column, self._user.id)
        )
        self._accessed = result[0]["accessed"]
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

    def _check_external(self) -> bool:
        """
        Check whether the user is listed as external user

        :return: bool
        """

        rows, values = _execute("SELECT * FROM externals WHERE external=%s", (self._id,))
        return rows == 0 and len(values) == 0

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
    def tid(self) -> typing.Optional[int]:
        return self._user.id

    @property
    def username(self) -> typing.Optional[str]:
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

    @permission.setter
    def permission(self, new: bool) -> None:
        self._permission = self._update_record("permission", bool(new))

    @property
    def active(self) -> bool:
        return bool(self._active)

    @property
    def created(self) -> _datetime.datetime:
        return self._created

    @property
    def accessed(self) -> _datetime.datetime:
        return self._accessed

    @property
    def user(self) -> typing.Optional[_telegram.User]:
        return self._user

    @property
    def virtual(self) -> bool:
        return self._tid is None

    @property
    def external(self) -> bool:
        return bool(self._external)

    @external.setter
    def external(self, new: bool):
        if bool(new) != self.external:
            if new:
                _execute("INSERT INTO externals (external) VALUES (%s)", (self._id,))
            else:
                _execute("DELETE FROM externals WHERE external=%s", (self._id,))
            self._external = self._check_external()


class CommunityUser(BaseBotUser):
    """
    Special user which receives consume transactions and sends payment transactions

    Note that this user is designed as a singleton. In order to get an
    updated CommunityUser, always use a fresh instance of this class.
    If there's not exactly one virtual user in the database, the
    constructor for this class fails. This means that you have to fix
    some issue with your data set manually to ensure further integrity.
    """

    _ALLOWED_UPDATES = ["balance"]

    def __init__(self):
        """
        :raises pymysql.err.DataError: when no virtual user was found
        :raises pymysql.err.IntegrityError: when multiple virtual users were found
        :raises pymysql.err.IntegrityError: when the user is marked external
        """

        rows, values = _execute("SELECT * FROM users WHERE tid IS NULL")

        if rows == 0 or len(values) == 0:
            raise _err.DataError(
                "No community user created yet! Do this manually and try again."
            )

        elif rows == 1 and len(values) == 1:
            self._unpack_record(values[0])
            if self._check_external():
                raise _err.IntegrityError(
                    "The community user is marked external! Fix this issue and try again."
                )

        else:
            raise _err.IntegrityError(
                "Multiple community users were found! Fix this issue and try again."
            )


class MateBotUser(BaseBotUser):
    """
    MateBotUser convenience class storing all information about a user

    Specify a Telegram User object to initialize this object. It will
    fetch all available data from the database in the background.
    Do not cache these values for consistency reasons.
    """

    _ALLOWED_UPDATES = ["username", "name", "balance", "permission"]

    def __init__(self, user: _telegram.User):
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
