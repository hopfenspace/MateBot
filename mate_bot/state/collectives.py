#!/usr/bin/env python3

"""
MateBot group transaction ("collective operation") base library
"""

import typing
import datetime

import pytz as _tz
import tzlocal as _local_tz

import err
from .user import MateBotUser
from .dbhelper import (
    execute as _execute,
    execute_no_commit as _execute_no_commit,
    EXECUTE_TYPE as _EXECUTE_TYPE
)


class BaseCollective:
    """
    Base class for collective operations

    This class is not usable without being modified (subclassed).
    For easy usability, at least a constructor is needed.
    """

    _id = None
    _active = False
    _amount = 0
    _externals = 0
    _description = ""
    _creator = None
    _created = None

    _communistic = None

    _ALLOWED_COLUMNS = []

    @staticmethod
    def _get_uid(user: typing.Union[int, MateBotUser]) -> int:
        """
        Extract the user ID from a given user object

        :param user: MateBotUser instance or integer
        :type user: typing.Union[int, MateBotUser]
        :return: user ID as integer
        :rtype: int
        :raises TypeError: when the user is neither int nor MateBotUser instance
        """

        if isinstance(user, MateBotUser):
            user = user.uid
        if not isinstance(user, int):
            raise TypeError("Expected integer or MateBotUser instance")
        return user

    @classmethod
    def get_cid_from_active_creator(
            cls,
            creator: typing.Union[int, MateBotUser]
    ) -> typing.Optional[int]:
        """
        Retrieve the collective's ID from the database using the creator's ID

        One user can only have exactly one active collective operation at a time.
        Therefore, this will only work when the user has an active collective.
        If not, it will return None. Otherwise, it returns the collective's ID.
        It may also raise a DesignViolation, when there's more than one result!

        :param creator: identification of the active collective's creator
        :type creator: typing.Union[int, user.MateBotUser]
        :return: internal collective's ID
        :raises err.DesignViolation: when more than one collective is active for this creator
        """

        creator = cls._get_uid(creator)
        rows, values = _execute(
            "SELECT id FROM collectives WHERE active=true AND creator=%s",
            (creator,)
        )

        if rows == 1 and len(values) == 1:
            return values[0]["id"]
        if rows > 1 and len(values) > 1:
            raise err.DesignViolation

    @classmethod
    def has_user_active_collective(cls, creator: typing.Union[int, MateBotUser]) -> bool:
        """
        Determine whether a given user has already an ongoing collective operation

        :param creator: MateBot user who may have started a collective operation
        :type creator: typing.Union[int, MateBotUser]
        :return: whether the user has already started a collective operation
        :rtype: bool
        """

        return cls.get_cid_from_active_creator(creator) is not None

    def __bool__(self) -> bool:
        """
        Determine whether the collective operation is still active

        This method returns False if the locally stored ID
        for the collective was not found in the database.

        :return: whether this collective operation is active
        :rtype: bool
        """

        rows, values = _execute("SELECT active FROM collectives WHERE id=%s", (self._id,))
        if rows == 0 and len(values) == 0:
            return False
        return bool(values[0]["active"])

    def _create_new_record(self) -> bool:
        """
        Create the record for the current collective in the database if it doesn't exist

        Note that the attribute `_communistic` must be
        present in order for this method to work properly.
        Remember that one user can only have one collective
        operation active at the same time.

        :return: whether the new record was created
        :rtype: bool
        :raises ValueError: when attribute values are wrong
        :raises TypeError: when attribute types don't match
        """

        if self.has_user_active_collective(self.creator):
            return False

        if not isinstance(self._communistic, bool):
            raise TypeError("Attribute isn't of type bool")
        if self._id is not None:
            raise ValueError("Internal ID is already set")
        if self._externals != 0:
            raise ValueError("No externals allowed for creation")

        connection = None
        try:
            connection = _execute_no_commit(
                "INSERT INTO collectives (amount, externals, description, communistic, creator) "
                "VALUES (%s, %s, %s, %s, %s)",
                (self._amount, 0, self._description, self._communistic, self._creator)
            )[2]

            rows, values, connection = _execute_no_commit(
                "SELECT LAST_INSERT_ID()",
                connection=connection
            )
            assert rows == 1
            self._id = values[0]["LAST_INSERT_ID()"]

            connection.commit()
            self.update()

        finally:
            if connection:
                connection.close()

        return True

    def _set_remote_value(self, column: str, value: typing.Union[str, int, bool, None]) -> None:
        """
        Set the remote value in a specific column and trigger .update()

        :param column: name of the column
        :type column: str
        :param value: value to be set for the current user in the specified column
        :type value: typing.Union[str, int, bool, None]
        :return: None
        :raises TypeError: when an invalid type for value is found
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

        if column not in self._ALLOWED_COLUMNS:
            raise RuntimeError("Operation not allowed")

        _execute(
            "UPDATE collectives SET {}=%s WHERE id=%s".format(column),
            (value, self._id)
        )

        rows, result = _execute(
            "SELECT * FROM collectives WHERE id=%s",
            (self._id,)
        )

        assert rows == 1
        return result[0][column]

    def _get_remote_record(self) -> _EXECUTE_TYPE:
        """
        Retrieve the remote record for the current collective (internal use only!)

        :return: number of affected rows and fetched data record
        """

        return _execute("SELECT * FROM collectives WHERE id=%s", (self._id,))

    def _get_remote_joined_record(self) -> _EXECUTE_TYPE:
        """
        Retrieve the joined remote records for the current collective (internal use only!)

        :return: number of affected rows and fetched data record
        """

        return _execute(
            "SELECT * FROM collectives "
            "LEFT JOIN collectives_users "
            "ON collectives.id=collectives_users.collectives_id "
            "WHERE collectives.id=%s",
            (self._id,)
        )

    def is_participating(
            self,
            user: typing.Union[int, MateBotUser]
    ) -> typing.Tuple[bool, typing.Optional[str]]:
        """
        Determine whether the user is participating in this collective operation

        :param user: MateBot user
        :type user: typing.Union[int, MateBotUser]
        :return: tuple whether the user is participating and the (optional) vote
        :rtype: typing.Tuple[bool, typing.Optional[str]]
        :raises err.DesignViolation: when more than one match was found
        """

        user = self._get_uid(user)
        rows, values = _execute(
            "SELECT * FROM collectives_users "
            "WHERE collectives_id=%s AND users_id=%s",
            (self._id, user)
        )

        if rows == 0 and len(values) == 0:
            return False, None
        if rows > 1 and len(values) > 1:
            raise err.DesignViolation
        return True, values[0]["vote"]

    def add_user(
            self,
            user: typing.Union[int, MateBotUser],
            vote: typing.Union[str, bool] = False
    ) -> bool:
        """
        Add a user to the collective using the given vote

        :param user: MateBot user
        :type user: typing.Union[int, MateBotUser]
        :param vote: positive or negative vote (ignored for certain operation types)
        :type vote: typing.Union[str, bool]
        :return: success of the operation
        :rtype: bool
        """

        user = self._get_uid(user)
        if isinstance(vote, bool):
            vote = "+" if vote else "-"
        if vote not in ("+", "-"):
            raise ValueError("Expected '+' or '-'")

        if not self._is_participating(user)[0]:
            rows, values = _execute(
                "INSERT INTO collectives_users(collectives_id, users_id, vote) "
                "VALUES (%s, %s, %s)",
                (self._id, user, vote)
            )

            return rows == 1 and len(values) == 1
        return False

    def remove_user(self, user: typing.Union[int, MateBotUser]) -> bool:
        """
        Remove a user from the collective

        :param user: MateBot user
        :type user: typing.Union[int, MateBotUser]
        :return: success of the operation
        :rtype: bool
        """

        user = self._get_uid(user)
        if self._is_participating(user)[0]:
            rows, values = _execute(
                "DELETE FROM collectives_users "
                "WHERE collectives_id=%s AND users_id=%s",
                (self._id, user)
            )

            return rows == 1 and len(values) == 1
        return False

    def toggle_user(
            self,
            user: typing.Union[int, MateBotUser],
            vote: typing.Union[str, bool] = False
    ) -> bool:
        """
        Add or remove a user to/from the collective using the given vote

        :param user: MateBot user
        :type user: typing.Union[int, MateBotUser]
        :param vote: positive or negative vote (ignored for certain operation types)
        :type vote: typing.Union[str, bool]
        :return: success of the operation
        :rtype: bool
        """

        if self._is_participating(user)[0]:
            return self.remove_user(user)
        else:
            return self.add_user(user, vote)

    def _abort(self) -> bool:
        """
        Abort the current pending collective operation without fulfilling the transactions

        :return: success of the operation
        :rtype: bool
        """

        if self._active:
            connection = None

            try:
                connection = _execute_no_commit(
                    "UPDATE collectives SET active=%s WHERE id=%s",
                    (False, self._id)
                )[2]
                _execute_no_commit(
                    "DELETE FROM collectives_users WHERE collectives_id=%s",
                    (self._id,),
                    connection=connection
                )

                connection.commit()

            finally:
                if connection:
                    connection.close()

            self._active = False

            return True
        return False

    def abort(self, user: MateBotUser) -> bool:
        """
        Abort the current pending collective operation without fulfilling the transactions

        Note that this will also delete the bindings which users
        participated in the collective operation without a possibility
        to restore it. The `user` parameter will only be used to
        check whether the user is permitted to perform this action.

        :param user: user who wants to abort the collective operation
        :type user: MateBotUser
        :return: success of the operation
        :rtype: bool
        """

        if user.uid != self._creator:
            return False

        return self._abort()

    def close(self) -> bool:
        """
        Close the collective operation and perform all transactions

        This method must be overwritten in a subclass!

        :return: success of the operation
        :rtype: bool
        """

        raise NotImplementedError

    def get(self) -> int:
        """
        Return the internal ID of the collective operation

        :return: internal ID
        :rtype: int
        """

        return self._id

    def update(self) -> bool:
        """
        Re-read the internal values from the database

        Important: This method ignores members of a collective operation.
        Only the attributes of the collective itself will be reloaded.

        :return: whether something has changed
        :rtype: bool
        """

        rows, values = self._get_remote_record()
        record = values[0]

        result = any([
            self._active != record["active"],
            self._amount != record["amount"],
            self._externals != record["externals"],
            self._description != record["description"],
            self._communistic != record["communistic"],
            self._creator != record["creator"],
            self._created != _tz.utc.localize(record["created"])
        ])

        if rows == 1:
            self._active = record["active"]
            self._amount = record["amount"]
            self._externals = record["externals"]
            self._description = record["description"]
            self._communistic = record["communistic"]
            self._creator = record["creator"]
            self._created = _tz.utc.localize(record["created"])

        return result and rows == 1

    @property
    def active(self) -> bool:
        """
        Get the active flag of the collective operation
        """

        return self._active

    @property
    def amount(self) -> int:
        """
        Get the amount (value) of the collective operation
        """

        return self._amount

    @property
    def description(self) -> typing.Optional[str]:
        """
        Get and set the description of the collective operation
        """

        return self._description

    @description.setter
    def description(self, new: typing.Optional[str]) -> None:
        if new is not None:
            if not isinstance(new, str):
                raise TypeError("Expected None or str")

        self._description = new
        self._set_remote_value("description", new)

    @property
    def creator(self) -> MateBotUser:
        """
        Get the creator of the collective operation
        """

        return self._creator

    @property
    def created(self) -> datetime.datetime:
        """
        Get the timestamp when the collective operation was created
        """

        return self._created.astimezone(_local_tz.get_localzone())
