"""
MateBot user definitions
"""

from __future__ import annotations
import typing
import datetime as _datetime

import pytz as _tz
import tzlocal as _local_tz
import pymysql.err as _err
import telegram as _telegram

from mate_bot.state.dbhelper import execute as _execute, EXECUTE_TYPE as _EXECUTE_TYPE


class BaseBotUser:
    """
    Base class for MateBot users

    This class is not usable without being modified (subclassed).
    For easy usability, at least a constructor is needed. Use
    the advanced subclasses MateBotUser or CommunityUser instead.
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
    _ALLOWED_EXTERNAL = False

    @classmethod
    def get_uid_from_tid(cls, tid: int) -> typing.Optional[int]:
        """
        Retrieve the user ID from the database using the Telegram ID as selector

        :param tid: Telegram user ID
        :type tid: int
        :return: int or None
        """

        rows, values = _execute("SELECT id FROM users WHERE tid=%s", (tid,))
        if rows == 1 and len(values) == 1:
            return values[0]["id"]
        return None

    @classmethod
    def get_tid_from_uid(cls, uid: int) -> typing.Optional[int]:
        """
        Retrieve the Telegram ID from the database using the user ID as selector

        :param uid: internal user ID
        :type uid: int
        :return: int or None
        """

        rows, values = _execute("SELECT tid FROM users WHERE id=%s", (uid,))
        if rows == 1 and len(values) == 1:
            return values[0]["tid"]
        return None

    @classmethod
    def get_name_from_uid(cls, uid: int) -> typing.Optional[str]:
        """
        Retrieve the stored name for the given user ID

        :param uid: internal user ID
        :type uid: int
        :return: str or None
        """

        rows, values = _execute("SELECT name FROM users WHERE id=%s", (uid,))
        if rows == 1 and len(values) == 1:
            return values[0]["name"]
        return None

    @classmethod
    def get_username_from_uid(cls, uid: int) -> typing.Optional[str]:
        """
        Retrieve the stored username for the given user ID

        :param uid:
        :return:
        """

        rows, values = _execute("SELECT username FROM users WHERE id=%s", (uid,))
        if rows == 1 and len(values) == 1:
            return values[0]["username"]
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
            return _execute("SELECT * FROM users WHERE tid=%s", (self._tid,))
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
        self._created = _tz.utc.localize(record["created"])
        self._accessed = _tz.utc.localize(record["accessed"])

    def _update_record(
            self,
            column: str,
            value: typing.Union[str, int, bool, None]
    ) -> typing.Union[str, int]:
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
            f"UPDATE users SET {column}=%s WHERE id=%s",
            (value, self._id)
        )

        rows, result = _execute(
            "SELECT * FROM users WHERE id=%s",
            (self._id,)
        )

        assert rows == 1
        self._accessed = _tz.utc.localize(result[0]["accessed"])
        return result[0][column]

    def _update_local(self, record: typing.Dict[str, typing.Any]) -> None:
        """
        Apply a database record to the local copy and check for consistency with Telegram

        :param record: database record as returned by a `SELECT * FROM users` query
        :type record: dict
        :return: None
        """

        self._unpack_record(record)

        if self._user:
            if self._name != self._user.full_name:
                self._name = self._update_record("name", self._user.full_name)
            if self._username != self._user.username:
                self._username = self._update_record("username", self._user.username)

    def check_external(self) -> bool:
        """
        Check whether the user is listed as external user

        :return: bool
        """

        rows, values = _execute("SELECT * FROM externals WHERE external=%s", (self._id,))
        return rows != 0 and len(values) != 0

    def update(self) -> None:
        """
        Re-read the internal values from the database

        :return: None
        """

        rows, values = self._get_remote_record(bool(self._tid))

        if rows == 1 and len(values) == 1:
            self._update_local(values[0])

        ext = self.check_external()
        if ext != self._external:
            self.external = ext

    @property
    def uid(self) -> int:
        """
        Get the internal user ID of a user
        """

        return self._id

    @property
    def tid(self) -> typing.Optional[int]:
        """
        Get the Telegram ID of a user

        This is None for virtual users.
        """

        if self._user is None:
            return self._tid
        return self._user.id

    @property
    def username(self) -> typing.Optional[str]:
        """
        Get and set the Telegram username of a user

        Note that this may be done automatically for non-virtual users by .update().
        The username is always prefixed with the @ symbol. Keep in mind that
        some users didn't set a username, which causes this method to return None.
        """

        if self._username is not None:
            if not self._username.startswith("@"):
                return "@" + self._username
        return self._username

    @username.setter
    def username(self, new: str) -> None:
        self.username = self._update_record("username", new)

    @property
    def name(self) -> str:
        """
        Get and set the Telegram name of a user

        Note that this may be done automatically for non-virtual users by .update().
        """

        return self._name

    @name.setter
    def name(self, new: str) -> None:
        self.name = self._update_record("name", new)

    @property
    def balance(self) -> int:
        """
        Get the current balance of a user measured in Cent
        """

        return self._balance

    @property
    def permission(self) -> bool:
        """
        Get and set the permission flag of a user

        Permissions are necessary to be able to vote.
        """

        return bool(self._permission)

    @permission.setter
    def permission(self, new: bool) -> None:
        self._permission = self._update_record("permission", bool(new))

    @property
    def active(self) -> bool:
        """
        Get and set the active flag of a user

        If a user is inactive, it can't perform some operations like sending money.
        """

        return bool(self._active)

    @active.setter
    def active(self, new: bool) -> None:
        self._active = self._update_record("active", bool(new))

    @property
    def created(self) -> _datetime.datetime:
        """
        Get the timestamp when the user was created in local time
        """

        return self._created.astimezone(_local_tz.get_localzone())

    @property
    def accessed(self) -> _datetime.datetime:
        """
        Get the timestamp when the user record was changed the last time in local time
        """

        return self._accessed.astimezone(_local_tz.get_localzone())

    @property
    def user(self) -> typing.Optional[_telegram.User]:
        """
        Get the Telegram User object of the user

        This is None for virtual users and objects that were created using the UID.
        """

        return self._user

    @property
    def virtual(self) -> bool:
        """
        Get the virtual flag of a user

        A user is virtual only if there's no valid Telegram ID.
        """

        return self._tid is None

    @property
    def external(self) -> bool:
        """
        Get and set the external flag of a user
        """

        return bool(self._external)

    @external.setter
    def external(self, new: bool):
        if bool(new) != self.external and self._ALLOWED_EXTERNAL:
            if new:
                _execute("INSERT INTO externals (external) VALUES (%s)", (self._id,))
            else:
                _execute("DELETE FROM externals WHERE external=%s", (self._id,))
            self._external = self.check_external()


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
    _ALLOWED_EXTERNAL = False

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
            if self.check_external():
                raise _err.IntegrityError(
                    "The community user is marked external! Fix this issue and try again."
                )

        else:
            raise _err.IntegrityError(
                "Multiple community users were found! Fix this issue and try again."
            )

    def __repr__(self) -> str:
        return "CommunityUser({self.name})"

    def __str__(self) -> str:
        return self.name


class MateBotUser(BaseBotUser):
    """
    MateBotUser convenience class storing all information about a user

    Specify a Telegram User object to initialize this object. It will
    fetch all available data from the database in the background.
    Do not cache these values for consistency reasons.
    If there is no record for this user in the database, a new
    one will be created implicitly. You can also pass an
    internal user ID to the constructor to use the record from
    the database to initialize the MateBotUser object.
    Note that the attribute `user` which normally holds the
    Telegram User object, will be set to None in this case.
    """

    _ALLOWED_UPDATES = ["username", "name", "balance", "permission", "active"]
    _ALLOWED_EXTERNAL = True

    def __init__(self, user: typing.Union[_telegram.User, int]):
        """
        :param user: the Telegram user to create a MateBotUser for (or its internal ID instead)
        :type user: telegram.User or int
        :raises TypeError: when the `user` is neither a Telegram User nor an int
        :raises pymysql.err.DataError: when the given user ID doesn't exist in the database
        """

        self._user = None

        if isinstance(user, _telegram.User):
            use_tid = True
            self._user = user
            self._tid = user.id

        elif isinstance(user, int):
            use_tid = False
            self._id = user

        else:
            raise TypeError(f"Invalid type {type(user)} for constructor")

        rows, values = self._get_remote_record(use_tid)

        existing = True
        if rows == 0 and len(values) == 0:
            existing = False

            if not use_tid:
                raise _err.DataError(f"User ID {self._id} was not found in the database.")

            _execute(
                "INSERT INTO users (tid, username, name) VALUES (%s, %s, %s)",
                (self._user.id, self._user.username, self._user.full_name)
            )

            rows, values = self._get_remote_record(use_tid)

        if rows == 1 and len(values) == 1:
            self._update_local(values[0])
            if not existing:
                self.external = True
            self._external = self.check_external()

    def __repr__(self) -> str:
        return f"MateBotUser(uid={self.uid}, tid={self.tid})"

    def __str__(self) -> str:
        result = self.name
        if self.username is not None:
            result += f" ({self.username})"
        return result

    @property
    def creditor(self):
        """
        Get and set the creditor user for a user

        When setting the creditor, only None, integers and other MateBotUser
        objects are allowed. None removes the current creditor user if there
        is one. An integer will be interpreted as user ID and transformed into
        a MateBotUser object. Lastly, MateBotUser objects are used to check
        if the creditor is an internal or external user. External users
        can't be creditors for other external users. Only external users
        need a creditor to be able to perform some kinds of operations.

        Note that the setter property might raise TypeErrors. Also
        note that this value is not cached in the MateBotUser object.
        Therefore, all getter and setter accesses produce SQL queries.
        """

        rows, values = _execute("SELECT internal FROM externals WHERE external=%s", (self._id,))
        if rows == 1 and len(values) == 1:
            return values[0]["internal"]
        return None

    @creditor.setter
    def creditor(self, new: typing.Union[None, int, BaseBotUser]):
        if new is not None:
            if not isinstance(new, (int, BaseBotUser)) or isinstance(new, CommunityUser):
                raise TypeError(f"Invalid type {type(new)} for creditor")

        if self.creditor != new:
            if new is None:
                _execute("UPDATE externals SET internal=NULL WHERE external=%s", (self._id,))
                return
            if isinstance(new, int) and new != CommunityUser().uid:
                new = MateBotUser(new)
            if not new.check_external():
                _execute("UPDATE externals SET internal=%s WHERE external=%s", (new.uid, self._id))

    @classmethod
    def get_worst_debtors(cls) -> typing.List[MateBotUser]:
        """
        Return a list of users with the highest debts

        :return: users with highest debts
        :rtype: typing.List[MateBotUser]
        """
        _, values = _execute("SELECT * FROM users WHERE tid IS NOT NULL AND balance=(SELECT MIN(balance) FROM users);")
        return list(MateBotUser(value["id"]) for value in values)
