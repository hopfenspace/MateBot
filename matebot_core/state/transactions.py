"""
MateBot money transaction (sending/receiving) helper library
"""

import os
import csv
import time
import typing
import logging
import tempfile

import pytz as _tz
import tzlocal as _local_tz
import telegram

from matebot_core.config import config
from matebot_core.state import user
from matebot_core.state.dbhelper import BackendHelper


logger = logging.getLogger("state")


class Transaction(BackendHelper):
    """
    Money transactions between two users

    Note that a transaction will not be committed and stored in
    persistent storage until the :meth:`commit` method was called!

    :param src: user that sends money to someone else
    :type src: user.BaseBotUser
    :param dst: user that receives money from someone else
    :type dst: user.BaseBotUser
    :param amount: money measured in Cent (must always be positive!)
    :type amount: int
    :param reason: optional description of / reason for the transaction
    :type reason: str or None
    :raises ValueError: when amount is not positive or sender=receiver
    :raises TypeError: when src or dst are no BaseBotUser objects or subclassed thereof
    """

    _src: user.BaseBotUser
    _dst: user.BaseBotUser
    _amount: int
    _reason: typing.Optional[str]

    _committed: bool
    _id: typing.Optional[int]

    def __init__(
            self,
            src: user.BaseBotUser,
            dst: user.BaseBotUser,
            amount: int,
            reason: typing.Optional[str] = None
    ):
        super().__init__()

        if amount <= 0:
            raise ValueError("Not a positive amount!")
        if not isinstance(src, user.BaseBotUser) or not isinstance(dst, user.BaseBotUser):
            raise TypeError("Expected BaseBotUser or its subclasses!")
        if src == dst:
            raise ValueError("Sender equals receiver of the transaction!")

        self._src = src
        self._dst = dst
        self._amount = int(amount)
        self._reason = reason

        self._committed = False
        self._id = None

    def __bool__(self) -> bool:
        return self._committed

    def get(self) -> typing.Optional[int]:
        """
        Return the internal ID of the transaction, if available (after committing)

        :return: internal ID of the transaction, if available
        :rtype: typing.Optional[int]
        """

        if self._committed:
            return self._id

    @property
    def src(self) -> user.BaseBotUser:
        """
        Get the sender of a transaction
        """

        return self._src

    @property
    def dst(self) -> user.BaseBotUser:
        """
        Get the receiver of a transaction
        """

        return self._dst

    @property
    def amount(self) -> int:
        """
        Get the height of the transaction (amount)
        """

        return self._amount

    @property
    def reason(self) -> typing.Optional[str]:
        """
        Get the optional reason for the transaction (description)
        """

        return self._reason

    @property
    def committed(self) -> bool:
        """
        Get the flag whether the transaction has been committed yet
        """

        return self._committed

    def log_info(self) -> None:
        """
        Create a short logging notification about the attempt to perform the transaction

        This method is not implemented in this class and provides a
        hook that might be implemented in a subclass. It will be
        called when the transaction was completed successfully.

        :return: None
        """

        pass

    def log_message(self) -> None:
        """
        Create a long logging information about the fulfilled transaction

        This method is not implemented in this class and provides a
        hook that might be implemented in a subclass. It will be
        called when the transaction was completed successfully.

        :return: None
        """

        pass

    def commit(self) -> None:
        """
        Fulfill the transaction and store it in the database persistently

        :raises RuntimeError: when amount is negative or zero or sender=receiver
        :raises TypeError: when the ``bot`` is not None and no ``telegram.Bot`` object
        :return: None
        """

        self.log_info()

        if self._amount < 0:
            raise RuntimeError("No negative transactions!")
        if self._amount == 0:
            raise RuntimeError("Empty transaction!")
        if self._src == self._dst:
            raise RuntimeError("Sender equals receiver!")

        if not self._committed and self._id is None:

            connection = None
            try:
                self._src.update()
                self._dst.update()

                connection = self._execute_no_commit(
                    "INSERT INTO transactions (sender, receiver, amount, reason) "
                    "VALUES (%s, %s, %s, %s)",
                    (self._src.uid, self._dst.uid, self._amount, self._reason)
                )[2]

                rows, values, _ = self._execute_no_commit(
                    "SELECT LAST_INSERT_ID()",
                    connection=connection
                )
                if rows == 1:
                    self._id = values[0]["LAST_INSERT_ID()"]

                self._execute_no_commit(
                    "UPDATE users SET balance=%s WHERE id=%s",
                    (self._src.balance - self.amount, self._src.uid),
                    connection=connection
                )
                self._execute_no_commit(
                    "UPDATE users SET balance=%s WHERE id=%s",
                    (self._dst.balance + self.amount, self._dst.uid),
                    connection=connection
                )

                connection.commit()

                self._src.update()
                self._dst.update()
                self._committed = True

            finally:
                if connection:
                    connection.close()

            self.log_message()


class LoggedTransaction(Transaction):
    """
    Money transactions between two users with enabled logging hooks

    Note that a transaction will not be committed and stored in
    persistent storage until the :meth:`commit` method was called!

    :param src: user that sends money to someone else
    :type src: user.BaseBotUser
    :param dst: user that receives money from someone else
    :type dst: user.BaseBotUser
    :param amount: money measured in Cent (must always be positive!)
    :type amount: int
    :param reason: optional description of / reason for the transaction
    :type reason: typing.Optional[str]
    :param bot: optional Telegram Bot object that will be used to send log messages
    :type bot: typing.Optional[telegram.Bot]
    :raises ValueError: when amount is not positive or sender=receiver
    :raises TypeError: when src or dst are no BaseBotUser objects or subclassed thereof
    """

    _bot: typing.Optional[telegram.Bot]

    def __init__(
            self,
            src: user.BaseBotUser,
            dst: user.BaseBotUser,
            amount: int,
            reason: typing.Optional[str] = None,
            bot: typing.Optional[telegram.Bot] = None
    ):
        super().__init__(src, dst, amount, reason)
        self._bot = bot

    def log_info(self) -> None:
        """
        Create a short logging notification about the transaction

        A short summary of the transaction will be send to the global ``logger``.

        :return: None
        """

        logger.info(
            f"Transferring {self.amount} from {self.src} to {self.dst} for '{self.reason}' ..."
        )

    def log_message(self) -> None:
        """
        Create a long logging information about the transaction

        A Markdown-formatted message will be send to all chat IDs
        configured to receive transaction log messages in the config file.

        :return: None
        """

        logger.debug(f"Transaction from {self.src} to {self.dst} fulfilled.")

        if self._bot is not None:
            if not isinstance(self._bot, telegram.Bot):
                raise TypeError(f"Expected telegram.Bot, but got {type(self._bot)}")
            transaction_logging = config["chats"]["transactions"]
            if isinstance(config["chats"]["transactions"], int):
                transaction_logging = [config["chats"]["transactions"]]
            for chat in transaction_logging:
                self._bot.send_message(
                    chat,
                    "*Incoming transaction*\n\n"
                    f"Sender: {self.src}\n"
                    f"Receiver: {self.dst}\n"
                    f"Amount: {self.amount / 100:.2f}€\n"
                    f"Reason: `{self.reason}`",
                    parse_mode="Markdown",
                    disable_notification=True
                )


class TransactionLog(BackendHelper):
    """
    Transaction history for a specific user based on the logs in the database

    When instantiating a TransactionLog object, one can filter the
    transactions based on their "direction" using the `mode` keyword.
    The default value of zero means that all transactions will be used.
    Any negative integer means that only negative operations (the specified
    user is the sender) will be used while any positive integer means that
    only positive operations will be used (the specified user is the receiver).

    :param uid: internal user ID or BaseBotUser instance (or subclass thereof)
    :type uid: typing.Union[int, user.BaseBotUser]
    :param limit: restrict the number of fetched entries
    :type limit: typing.Optional[int]
    """

    _uid: int
    _limit: typing.Optional[int]
    _valid: bool
    _log: list
    _names: dict

    DEFAULT_NULL_REASON_REPLACE = "<no description>"

    @staticmethod
    def format_entry(
            amount: int,
            direction: str,
            partner: str,
            reason: str,
            timestamp: str
    ) -> str:
        """
        Format a single entry of the transaction history into a string record

        A subclass may override this staticmethod to easily change the formatted output.

        :param amount: amount of money in the current transaction measured in Cent
        :type amount: int
        :param direction: direction as returned by .get_direction()
        :type direction: str
        :param partner: name of the other part of a transaction as returned by .get_name()
        :type partner: str
        :param reason: description / reason of the transaction
        :type reason: str
        :param timestamp: timestamp of the record as returned by .format_time()
        :type timestamp: str
        :return: fully formatted string containing exactly one transaction
        :rtype: str
        """

        return f"{timestamp}: {amount:>+6.2f}: me {direction} {partner:<16} :: {reason}"

    @staticmethod
    def format_time(time_tuple: time.struct_time) -> str:
        """
        Format a timestamp to a string

        :param time_tuple: timestamp as returned by datetime.datetime.timetuple()
        :type time_tuple: time.struct_time
        :return: formatted string
        :rtype: str
        """

        return time.strftime('%d.%m.%Y %H:%M', time_tuple)

    @staticmethod
    def get_direction(incoming: bool) -> str:
        """
        Return a short descriptive string that shows the direction of a transaction

        A subclass may override this staticmethod to easily change the formatted output.

        :param incoming: switch whether the transaction is incoming (positive) or outgoing (negative)
        :type incoming: bool
        :return: short string to describe the direction of a transaction
        :rtype: str
        """

        return "<<" if incoming else ">>"

    def __init__(
            self,
            uid: typing.Union[int, user.BaseBotUser],
            limit: typing.Optional[int] = None
    ):

        if isinstance(uid, int):
            self._uid = uid
        elif isinstance(uid, user.BaseBotUser):
            self._uid = uid.uid
        else:
            raise TypeError(f"UID of bad type {type(uid)}")

        if limit is not None:
            if not isinstance(limit, int):
                raise TypeError(f"Expected int, not {type(limit)}")

        self._limit = limit
        self._names = {}

        extension = ""
        params = (self._uid, self._uid)
        if self._limit is not None:
            extension = " ORDER BY registered DESC LIMIT %s"
            params = (self._uid, self._uid, self._limit)

        rows, self._log = self._execute(
            "SELECT * FROM transactions WHERE sender=%s OR receiver=%s" + extension,
            params
        )

        self._valid = True
        if rows == 0 and user.BaseBotUser.get_tid_from_uid(self._uid) is None:
            self._valid = False
        if len(self._log) == 0:
            self._log = []

        if self._limit is not None:
            self._log.reverse()

        validity_check = self.validate()
        if validity_check is not None:
            self._valid = self._valid and validity_check

    def get_name(self, uid: int) -> typing.Optional[str]:
        """
        Convert a user ID of a user in the database to a name (or something else)

        A subclass may override this method to easily change the formatted output.
        However, this method also performs basic memoization to reduce database calls.
        Note that this method may return ``None`` for unknown user IDs.

        :param uid: internal user ID of a MateBot user
        :type uid: int
        :return: name of the MateBot user (or ``None`` for unknown user IDs)
        :rtype: typing.Optional[str]
        """

        if uid in self._names:
            return self._names[uid]

        name = user.BaseBotUser.get_name_from_uid(uid)
        if name is None:
            return

        self._names[uid] = name
        return name

    def to_list(self, localized: bool = config["general"]["db-localtime"]) -> typing.List[str]:
        """
        Return a list of pretty formatted transaction log entries

        :param localized: switch whether the database already has localized timestamps
        :type localized: bool
        :return: list of fully formatted strings including all transactions of a user
        :rtype: typing.List[str]
        """

        logs = []
        for entry in self._log:
            amount = entry["amount"] / 100
            reason = entry["reason"]
            if entry["reason"] is None:
                reason = self.DEFAULT_NULL_REASON_REPLACE

            if entry["receiver"] == self._uid:
                direction = self.get_direction(True)
                partner = self.get_name(entry["sender"])
            elif entry["sender"] == self._uid:
                direction = self.get_direction(False)
                partner = self.get_name(entry["receiver"])
                amount = -amount
            else:
                raise RuntimeError

            tz = _local_tz.get_localzone()
            if localized:
                ts = tz.localize(entry["registered"])
            else:
                ts = _tz.utc.localize(entry["registered"]).astimezone(tz)

            logs.append(self.format_entry(amount, direction, partner, reason, self.format_time(ts.timetuple())))

        return logs

    def to_string(self, localized: bool = config["general"]["db-localtime"], sep: str = os.sep) -> str:
        """
        Return a list of pretty formatted transaction log entries

        :param localized: switch whether the database already has localized timestamps
        :type localized: bool
        :param sep: character to use as line separator (defaults to OS-default newline character)
        :type sep: str
        :return: list of fully formatted strings including all transactions of a user
        :rtype: typing.List[str]
        :raises TypeError: when `sep` is no string
        """

        if not isinstance(sep, str):
            raise TypeError(f"Expected str, found {type(sep)}")

        return sep.join(self.to_list(localized))

    def to_json(self) -> typing.List[typing.Dict[str, typing.Union[int, str]]]:
        """
        Return a JSON-serializable list of transaction entries

        Note that the datetime objects will be converted to integers representing UNIX timestamps.

        :return: list
        """

        result = []
        for entry in self._log:
            result.append(entry.copy())
            result[-1]["registered"] = int(result[-1]["registered"].timestamp())
        return result

    def to_csv(self, strict: bool = False) -> typing.Optional[str]:
        """
        Return a valid CSV-formatted string of the user's full transaction history

        :param strict: switch whether the method returns ``None`` for an empty history,
            otherwise a CSV-formatted string of the headers (only) would be returned)
        :type strict: bool
        :return: CSV-formatted string of the user's transaction history
        :rtype: typing.Optional[str]
        """

        logs = [{
            "id": entry["id"],
            "sender": self.get_name(entry["sender"]),
            "receiver": self.get_name(entry["receiver"]),
            "amount": entry["amount"],
            "cumulative": -entry["amount"] if entry["sender"] == self.uid else entry["amount"],
            "reason": entry["reason"],
            "registered": entry["registered"].isoformat()
        } for entry in self._log]

        if strict and len(logs) == 0:
            return

        with tempfile.TemporaryFile(mode="w+") as file:
            writer = csv.DictWriter(file, fieldnames=logs[0].keys(), quoting=csv.QUOTE_ALL)
            writer.writeheader()
            writer.writerows(logs)
            file.seek(0)
            content = file.read()

        return content

    def validate(self, start: int = 0) -> typing.Optional[bool]:
        """
        Validate the history and verify integrity (full history since start of the logs)

        This method is only useful for full history checks and therefore
        returns None not all data was fetched from the database by setting a limit.

        :param start: balance of the user when it was first created (should be zero)
        :type start: int
        :return: history's validity
        :rtype: typing.Optional[bool]
        """

        if self._limit is not None:
            return None

        current = user.MateBotUser(self._uid).balance

        for entry in self._log:
            if entry["receiver"] == self._uid:
                start += entry["amount"]
            elif entry["sender"] == self._uid:
                start -= entry["amount"]
            else:
                raise RuntimeError

        return start == current

    @property
    def uid(self) -> int:
        """
        Get the internal user ID for which the log was created
        """

        return self._uid

    @property
    def valid(self) -> bool:
        """
        Get the valid flag which is set when the transaction log seems to be complete and correct
        """

        return self._valid

    @property
    def history(self) -> typing.List[typing.Dict[str, typing.Any]]:
        """
        Get the raw data of the user's transaction history
        """

        return self._log
