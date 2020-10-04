"""
MateBot group transaction ("collective operation") base library
"""

import typing
import datetime

import pytz as _tz
import tzlocal as _local_tz
import telegram

from mate_bot import err
from mate_bot.state.base import LoggerBase
from mate_bot.state.user import MateBotUser
from mate_bot.state.dbhelper import BackendHelper, EXECUTE_TYPE as _EXECUTE_TYPE


class BaseCollective(BackendHelper, LoggerBase):
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
    def get_type(cls, collective_id: int) -> int:
        """
        Retrieve the type of the collective with the given ID

        :param collective_id: collective ID to search for in the database
        :type collective_id: int
        :return: type flag of the remotely stored collective ID
        :rtype: int
        :raises IndexError: when the collective ID does not match exactly one record
        """

        rows, values = super().get_value("collectives", "communistic", collective_id)
        if rows != 1:
            raise IndexError(f"Collective ID {collective_id} not found")
        return values[0]["communistic"]

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
        rows, values = cls._execute(
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

        rows, values = self.get_value("collectives", "active", self._id)
        if rows == 0 and len(values) == 0:
            return False
        return bool(values[0]["active"])

    def _create_new_record(self) -> bool:
        """
        Create the record for the current collective in the database if it doesn't exist

        Note that the attribute :attr:`_communistic` must be
        present in order for this method to work properly.
        Remember that one user can only have one active
        collective operation at the same time.

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
        if self._externals != 0 and self._externals is not None:
            raise ValueError("No externals allowed for creation")

        connection = None
        try:
            connection = self._execute_no_commit(
                "INSERT INTO collectives (amount, externals, description, communistic, creator) "
                "VALUES (%s, %s, %s, %s, %s)",
                (self._amount, 0, self._description, self._communistic, self._creator)
            )[2]

            rows, values, connection = self._execute_no_commit(
                "SELECT LAST_INSERT_ID()",
                connection=connection
            )
            self._id = values[0]["LAST_INSERT_ID()"]

            connection.commit()
            self.update()

        finally:
            if connection:
                connection.close()

        return True

    def _set_remote_value(self, column: str, value: typing.Union[str, int, bool, None]) -> None:
        """
        Set the remote value in a specific column

        :param column: name of the column
        :type column: str
        :param value: value to be set for the current user in the specified column
        :type value: typing.Union[str, int, bool, None]
        :return: None
        :raises TypeError: when an invalid type for value is found
        :raises RuntimeError: when the column is not marked writeable by configuration
        """

        if column not in self._ALLOWED_COLUMNS:
            raise RuntimeError("Operation not allowed")

        self.set_value("collectives", column, self._id, value)

    def _get_remote_record(self) -> _EXECUTE_TYPE:
        """
        Retrieve the remote record for the current collective (internal use only!)

        :return: number of affected rows and fetched data record
        """

        return self.get_value("collectives", None, self._id)

    def _get_remote_joined_record(self) -> _EXECUTE_TYPE:
        """
        Retrieve the joined remote records for the current collective (internal use only!)

        :return: number of affected rows and fetched data record
        """

        return self._execute(
            "SELECT * FROM collectives "
            "LEFT JOIN collectives_users "
            "ON collectives.id=collectives_users.collectives_id "
            "WHERE collectives.id=%s",
            (self._id,)
        )

    def get_users_ids(self) -> typing.List[int]:
        """
        Return a list of participating users' internal IDs

        :return: list of users' internal IDs
        :rtype: typing.List[int]
        """

        return list(map(
            lambda r: r["users_id"],
            filter(
                lambda r: r["users_id"] is not None,
                self._get_remote_joined_record()[1]
            )
        ))

    def get_users_names(self) -> typing.List[str]:
        """
        Return a list of participating users' names

        :return: list of users' names
        :rtype: typing.List[str]
        """

        return list(map(lambda x: MateBotUser(x).name, self.get_users_ids()))

    def get_users(self) -> typing.List[MateBotUser]:
        """
        Return a list of participating users as MateBotUser objects

        :return: list of users as MateBotUser objects
        :rtype: typing.List[MateBotUser]
        """

        return list(map(MateBotUser, self.get_users_ids()))

    def get_messages(self, chat: typing.Optional[int] = None) -> typing.List[typing.Tuple[int, int]]:
        """
        Get the list of registered messages that handle the current collective

        Every item of the returned list is a tuple whose first integer
        is the Telegram Chat ID while the second one is the Telegram
        Message ID inside this chat. Use the combination of both to
        refer to the specific message that contains the inline keyboard.

        :param chat: when given, only the messages for this chat will be returned
        :type chat: typing.Optional[int]
        :return: list of all registered messages
        :rtype: typing.List[typing.Tuple[int, int]]
        :raises TypeError: when the chat ID is no integer
        """

        if chat is not None:
            if not isinstance(chat, int):
                raise TypeError("Expected optional integer as argument")

        result = []
        for record in self.get_values_by_key("collective_messages", "collectives_id", self._id)[1]:
            result.append((record["chat_id"], record["msg_id"]))

        if chat is not None:
            result = list(filter(lambda r: r[0] == chat, result))
        return result

    def register_message(self, chat: int, msg: int) -> bool:
        """
        Register a Telegram message for the current collective

        Note that it is important to verify the return value of this
        method. It will not raise exceptions in case there's already
        a message in the specified chat, it will fail silently.

        :param chat: Telegram Chat ID
        :type chat: int
        :param msg: Telegram Message ID inside the specified chat
        :type msg: int
        :return: success of the operation
        :rtype: bool
        :raises TypeError: when the method arguments are no integers
        """

        if not isinstance(chat, int) or not isinstance(msg, int):
            raise TypeError("Expected integers as arguments")

        for record in self.get_messages():
            if record[0] == chat:
                return False

        return self._execute(
            "INSERT INTO collective_messages (collectives_id, chat_id, msg_id) VALUES (%s, %s, %s)",
            (self._id, chat, msg)
        )[0] == 1

    def unregister_message(self, chat: int, msg: int) -> bool:
        """
        Unregister a Telegram message for the current collective

        Note that it is important to verify the return value of this
        method. It will not raise exceptions in case the specified
        message could not be found, it will fail silently.

        :param chat: Telegram Chat ID
        :type chat: int
        :param msg: Telegram Message ID inside the specified chat
        :type msg: int
        :return: success of the operation
        :rtype: bool
        :raises TypeError: when the method arguments are no integers
        """

        if not isinstance(chat, int) or not isinstance(msg, int):
            raise TypeError("Expected integers as arguments")

        return self._execute(
            "DELETE FROM collective_messages WHERE collectives_id=%s AND chat_id=%s AND msg_id=%s",
            (self._id, chat, msg)
        )[0] == 1

    def replace_message(self, chat: int, msg: int) -> bool:
        """
        Replace the currently stored message in the chat with the new ID

        Note that it is important to verify the return value of this
        method. It will not raise exceptions in case the specified chat
        didn't store any old message, it will silently create the record.

        :param chat: Telegram Chat ID
        :type chat: int
        :param msg: old Telegram Message ID inside the specified chat
        :type msg: int
        :return: success of the operation
        :rtype: bool
        :raises TypeError: when the method arguments are no integers
        """

        if not isinstance(chat, int) or not isinstance(msg, int):
            raise TypeError("Expected integers as arguments")

        if not self._execute(
            "UPDATE collective_messages SET msg_id=%s WHERE collectives_id=%s AND chat_id=%s",
            (msg, self._id, chat)
        )[0]:
            return self.register_message(chat, msg)
        return True

    def is_participating(
            self,
            user: typing.Union[int, MateBotUser]
    ) -> typing.Tuple[bool, typing.Optional[bool]]:
        """
        Determine whether the user is participating in this collective operation

        :param user: MateBot user
        :type user: typing.Union[int, MateBotUser]
        :return: tuple whether the user is participating and the (optional) vote
        :rtype: typing.Tuple[bool, typing.Optional[bool]]
        :raises err.DesignViolation: when more than one match was found
        """

        user = self._get_uid(user)
        rows, values = self._execute(
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
            vote: typing.Union[bool] = False
    ) -> bool:
        """
        Add a user to the collective using the given vote

        :param user: MateBot user
        :type user: typing.Union[int, MateBotUser]
        :param vote: positive or negative vote (ignored for certain operation types)
        :type vote: typing.Union[str, bool]
        :return: success of the operation
        :rtype: bool
        :raises TypeError: when the vote is no boolean
        """

        user = self._get_uid(user)
        if not isinstance(vote, bool):
            raise TypeError("Expected boolean value for vote")

        if not self.is_participating(user)[0]:
            rows, values = self._execute(
                "INSERT INTO collectives_users(collectives_id, users_id, vote) "
                "VALUES (%s, %s, %s)",
                (self._id, user, vote)
            )

            return rows == 1
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
        if self.is_participating(user)[0]:
            rows, values = self._execute(
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

        if self.is_participating(user)[0]:
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
                connection = self.set_value_manually("collectives", "active", self._id, False)[2]
                self._execute_no_commit(
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
        :raises IndexError: when the ID did not return a remote record
        :raises TypeError: when the remote record is of a wrong collective type
        """

        rows, values = self._get_remote_record()
        record = values[0]

        if type(self)._communistic != record["communistic"]:
            raise TypeError(f"Remote record for {self._id} is not compatible with {type(self)}")

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

    def edit_all_messages(
            self,
            content: str,
            markup: telegram.InlineKeyboardMarkup,
            bot: telegram.Bot,
            parse_mode: str = "Markdown"
    ) -> None:
        """
        Edit the content of the collective messages in all chats

        :param content: message context as text (with support according to ``parse_mode``
        :type content: str
        :param markup: inline keyboard that should be used for the messages
        :type markup: telegram.InlineKeyboardMarkup
        :param bot: Telegram Bot object
        :type bot: telegram.Bot
        :param parse_mode: parse mode of the message content (default: Markdown)
        :type parse_mode: str
        :return: None
        """

        for c, m in self.get_messages():
            bot.edit_message_text(
                content,
                chat_id=c,
                message_id=m,
                reply_markup=markup,
                parse_mode=parse_mode
            )

    @property
    def active(self) -> bool:
        """
        Get and set the active flag of the collective operation
        """

        return bool(self._active)

    @active.setter
    def active(self, new: bool) -> None:
        self._set_remote_value("active", bool(new))
        self.update()

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

        return MateBotUser(self._creator)

    @property
    def created(self) -> datetime.datetime:
        """
        Get the timestamp when the collective operation was created
        """

        return self._created.astimezone(_local_tz.get_localzone())
