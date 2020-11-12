"""
MateBot group transaction ("collective operation") base library
"""

import typing
import logging
import datetime

import pytz as _tz
import tzlocal as _local_tz
import telegram

from mate_bot import err
from mate_bot.config import config
from mate_bot.collectives.coordinators import MessageCoordinator, UserCoordinator
from mate_bot.state.user import MateBotUser
from mate_bot.state.dbhelper import EXECUTE_TYPE as _EXECUTE_TYPE


logger = logging.getLogger("collectives")

_CREATION_ARGUMENTS = typing.Tuple[MateBotUser, int, str, typing.Optional[telegram.Message]]
COLLECTIVE_ARGUMENTS = typing.Union[int, _CREATION_ARGUMENTS]


class BaseCollective(MessageCoordinator, UserCoordinator):
    """
    Base class for collective operations

    Keep in mind that this class uses multiple inheritance:

    .. image:: collectives_hierarchy.png

    :param arguments: either an internal ID of an existing collective operation or a tuple
        of arguments to create a new collective operation based on those supplied values
    :param default_externals: default value to use for collective operations
        (note that ``None`` is not just a placeholder but a valid default value instead!)
    :raises ValueError: when a supplied argument has an invalid value
    :raises TypeError: when a supplied argument has the wrong type
    :raises RuntimeError: when the collective ID doesn't match the class definition
        or when the class did not properly define its collective type using the class
        attribute ``_communistic`` (which is ``None`` by default and should be set properly)
    """

    _id: int = None
    _active: bool = False
    _amount: int = 0
    _externals: int = 0
    _description: str = ""
    _creator: int = None
    _created: datetime.datetime = None

    _communistic: bool = None

    _ALLOWED_COLUMNS: typing.List[str] = []

    def __init__(
            self,
            arguments: COLLECTIVE_ARGUMENTS,
            default_externals: typing.Union[int, None]
    ):
        if type(self)._communistic is None:
            raise RuntimeError("You need to set '_communistic' in a subclass")

        if isinstance(arguments, int):
            self._id = arguments
            self.update()
            if type(self)._communistic != self._communistic:
                raise RuntimeError("Remote record does not match collective operation type")

        elif isinstance(arguments, tuple):
            self._handle_tuple_constructor_argument(arguments, default_externals)

        else:
            raise TypeError("Expected int or tuple of arguments")

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

    def _handle_tuple_constructor_argument(
            self,
            arguments: _CREATION_ARGUMENTS,
            externals: typing.Union[int, None]
    ) -> None:
        """
        Handle the tuple argument of the classes' constructors

        The constructor of the :class:`BaseCollective` accepts either a single integer
        or a tuple of arguments. The handling of the tuple is very similar in
        the currently implemented subclasses. The tuple contains either three
        or four elements (because the fourth element is considered optional).

        If the tuple has three values, the following types are excepted:

        * :class:`mate_bot.state.user.MateBotUser` as initiating user (creator)
        * ``int`` as amount of the collective operation
        * ``str`` as reason for the collective operation

        If the tuple has four values, the following types are excepted:

        * :class:`mate_bot.state.user.MateBotUser` as initiating user (creator)
        * ``int`` as amount of the collective operation
        * ``str`` as reason for the collective operation
        * ``telegram.Message`` as message that initiated the collective

        Afterwards, a new collective operation will be created. The given MateBot
        user will be stored as creator for the collective. The amount and reason
        values are self-explanatory. The last value is the message that contains the
        command to start the new collective operation and will be used to reply to.
        As it is considered optional, no reply will be sent if the fourth value
        is absent or set to ``None`` to make the collective independent of Telegram.

        :param arguments: collection of arguments as described above
        :param externals: optional number of external users that joined the collective
            (note that ``None`` is not just a placeholder but a valid default value instead!)
        :type externals: typing.Union[int, None]
        :return: None
        :raises ValueError: when the tuple does not contain three or four elements
        :raises TypeError: when the values in the tuple have wrong types
        """

        if len(arguments) == 3:
            user, amount, reason = arguments
            message = None

        elif len(arguments) == 4:
            user, amount, reason, message = arguments

        else:
            raise ValueError("Expected three or four arguments for the tuple")

        if not isinstance(user, MateBotUser):
            raise TypeError("Expected MateBotUser object as first element")
        if not isinstance(amount, int):
            raise TypeError("Expected int object as second element")
        if not isinstance(reason, str):
            raise TypeError("Expected str object as third element")

        self._creator = user.uid
        self._amount = amount
        self._description = reason
        self._externals = externals
        self._active = True

        self._create_new_record()
        logger.info(f"New collective by {user.name} of {amount} for '{reason}' (ID {self._id})")

        if message is not None:
            if not isinstance(message, telegram.Message):
                raise TypeError("Expected optional telegram.Message as fourth element")

            reply = message.reply_markdown(
                self.get_markdown(),
                reply_markup=self._get_inline_keyboard()
            )
            self.register_message(reply.chat_id, reply.message_id)
            logger.debug(f"Sent reply message {reply.message_id} to chat {reply.chat_id}")

            if message.chat_id != config["chats"]["internal"]:
                msg = message.bot.send_message(
                    config["chats"]["internal"],
                    self.get_markdown(),
                    reply_markup=self._get_inline_keyboard(),
                    parse_mode="Markdown"
                )
                self.register_message(msg.chat_id, msg.message_id)
                logger.debug(f"Sent reply message {reply.message_id} to internal chat")

        else:
            logger.debug("No reply message has been sent")

    def get_core_info(self) -> str:
        """
        Retrieve the basic information for the collective's management message

        The returned string may be formatted using Markdown. The string
        should be suitable to be re-used inside :meth:`get_markdown`.

        :return: description message of the collective operation
        :rtype: str
        """

        raise NotImplementedError

    def _get_inline_keyboard(self) -> telegram.InlineKeyboardMarkup:
        """
        Get the inline keyboard to control the payment operation

        :return: inline keyboard using callback data strings
        :rtype: telegram.InlineKeyboardMarkup
        """
        raise NotImplementedError

    def get_markdown(self, status: typing.Optional[str] = None) -> str:
        """
        Generate the full message text as markdown string

        :param status: extended status information about the collective operation (Markdown supported)
        :type status: typing.Optional[str]
        :return: full message text as markdown string
        :rtype: str
        """

        raise NotImplementedError

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

    def _abort(self) -> bool:
        """
        Abort the current pending collective operation without fulfilling the transactions

        :return: success of the operation
        :rtype: bool
        """

        logger.debug(f"Aborting collective {self._id}...")

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

    def close(self, bot: typing.Optional[telegram.Bot] = None) -> bool:
        """
        Close the collective operation and perform all transactions

        This method must be overwritten in a subclass!

        :param bot: optional Telegram Bot object that sends transaction logs to some chat(s)
        :type bot: typing.Optional[telegram.Bot]
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

        static_error_message = (
            "Message is not modified: specified new message content and reply markup "
            "are exactly the same as a current content and reply markup of the message"
        )

        for c, m in self.get_messages():
            try:
                bot.edit_message_text(
                    content,
                    chat_id=c,
                    message_id=m,
                    reply_markup=markup,
                    parse_mode=parse_mode
                )

            except telegram.error.BadRequest as exc:
                if str(exc) == static_error_message:
                    logger.warning(
                        "Ignoring telegram.error.BadRequest exception in edit_all_messages",
                        exc_info=True
                    )
                else:
                    raise

    def forward(
            self,
            receiver: MateBotUser,
            bot: telegram.Bot,
            sender: typing.Optional[MateBotUser] = None
    ) -> None:
        """
        Forward the collective management message to another user

        In case the argument ``sender`` is given, a second message will be added as a
        reply to the actual management message to inform the receiver about the sender.
        This allows the receiver to contact the sender and e.g. ask questions about it.

        :param receiver: user that should receive a copy of the collective in private chat
        :type receiver: MateBotUser
        :param bot: the Telegram Bot that's used to send messages
        :type bot: telegram.Bot
        :param sender: optional user that forwarded the collective operation
        :type sender: typing.Optional[MateBotUser]
        :return: None
        """

        if not isinstance(receiver, MateBotUser):
            raise TypeError(f"Expected MateBotUser object as receiver, but got {type(receiver)}")
        if not isinstance(bot, telegram.Bot):
            raise TypeError(f"Expected telegram.Bot object as bot, but got {type(bot)}")

        forwarded = bot.send_message(
            chat_id=receiver.tid,
            text=self.get_markdown(),
            reply_markup=self._get_inline_keyboard(),
            parse_mode="Markdown"
        )

        for c, m in self.get_messages(forwarded.chat_id):
            bot.edit_message_text(
                chat_id=c,
                message_id=m,
                text=self.get_markdown(
                    "_\nThis management message has been disabled. Look below in this "
                    "chat to get a more recent version with updated content._"
                ),
                reply_markup=telegram.InlineKeyboardMarkup([]),
                parse_mode="Markdown"
            )

        self.replace_message(forwarded.chat_id, forwarded.message_id)

        if forwarded.chat_id != config["chats"]["internal"] and sender is not None:
            forwarded.reply_text(
                f"Note that you receive this message because {sender} forwarded it to you."
            )

        logger.debug(f"Forwarded collective {self._id} to {receiver} by {sender or 'someone'}")

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
