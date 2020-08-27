#!/usr/bin/env python3

import time
import typing

from . import user
from . import dbhelper as _db


class Transaction:
    """
    Money transactions between two users

    Note that a transaction will not be committed and stored in
    persistent storage until the .commit() method was called!
    """

    def __init__(
            self,
            src: user.BaseBotUser,
            dst: user.BaseBotUser,
            amount: int,
            reason: typing.Optional[str] = None
    ):
        """
        :param src: user that sends money to someone else
        :type src: user.BaseBotUser
        :param dst: user that receives money from someone else
        :type dst: user.BaseBotUser
        :param amount: money measured in Cent (must always be positive!)
        :type amount: int
        :param reason: optional description of / reason for the transaction
        :type reason: str or None
        :raises ValueError: when amount is not positive
        :raises TypeError: when src or dst are no BaseBotUser objects or subclassed thereof
        """

        if amount <= 0:
            raise ValueError("Not a positive amount!")
        if not isinstance(src, user.BaseBotUser) or not isinstance(dst, user.BaseBotUser):
            raise TypeError("Expected BaseBotUser or its subclasses!")

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
        return self._src

    @property
    def dst(self) -> user.BaseBotUser:
        return self._dst

    @property
    def amount(self) -> int:
        return self._amount

    @property
    def reason(self) -> str:
        return self._reason

    @property
    def committed(self) -> bool:
        return self._committed

    def commit(self) -> None:
        """
        Fulfill the transaction and store it in the database persistently

        :raises RuntimeError: when amount is negative or zero
        :return: None
        """

        if self._amount < 0:
            raise RuntimeError("No negative transactions!")
        if self._amount == 0:
            raise RuntimeError("Empty transaction!")

        if not self._committed and self._id is None:
            connection = None
            try:
                self._src.update()
                self._dst.update()

                connection = _db.execute_no_commit(
                    "INSERT INTO transactions (sender, receiver, amount, reason) "
                    "VALUES (%s, %s, %s, %s)",
                    (self._src.uid, self._dst.uid, self._amount, self._reason)
                )[2]

                rows, values, _ = _db.execute_no_commit("SELECT LAST_INSERT_ID()", connection = connection)
                if rows == 1:
                    self._id = values[0]["LAST_INSERT_ID()"]

                _db.execute_no_commit(
                    "UPDATE users SET balance=%s WHERE id=%s",
                    (self._src.balance - self.amount, self._src.uid),
                    connection = connection
                )
                _db.execute_no_commit(
                    "UPDATE users SET balance=%s WHERE id=%s",
                    (self._dst.balance + self.amount, self._dst.uid),
                    connection = connection
                )

                connection.commit()

                self._src.update()
                self._dst.update()
                self._committed = True

            finally:
                if connection:
                    connection.close()


class TransactionLog:
    """
    Transaction history for a specific user based on the logs in the database
    """

    DEFAULT_NULL_REASON_REPLACE = "<no description>"

    def __init__(self, uid: typing.Union[int, user.BaseBotUser], mode: int = 0):
        """
        :param uid: internal user ID or BaseBotUser instance (or subclass thereof)
        :type uid: int or user.BaseBotUser
        :param mode: direction of listed transactions (negative means from, positive means to, zero means both)
        :type mode: int
        """

        if isinstance(uid, int):
            self._uid = uid
        elif isinstance(uid, user.BaseBotUser):
            self._uid = uid.uid
        else:
            raise TypeError("UID of bad type {}".format(type(uid)))

        self._mode = mode

        if self._mode < 0:
            rows, self._log = _db.execute(
                "SELECT * FROM transactions WHERE sender=%s",
                (self._uid,)
            )
        elif self._mode > 0:
            rows, self._log = _db.execute(
                "SELECT * FROM transactions WHERE receiver=%s",
                (self._uid,)
            )
        else:
            rows, self._log = _db.execute(
                "SELECT * FROM transactions WHERE sender=%s OR receiver=%s",
                (self._uid, self._uid)
            )

        self._valid = True
        if rows == 0 and user.BaseBotUser.get_tid_from_uid(self._uid) is None:
            self._valid = False
        if len(self._log) == 0:
            self._log = []

    def to_string(self) -> str:
        """
        Return a pretty formatted version of the transaction log

        :return: str
        """

        logs = []
        for entry in self._log:
            amount = entry["amount"] / 100
            reason = entry["reason"]
            if entry["reason"] is None:
                reason = self.DEFAULT_NULL_REASON_REPLACE

            if entry["receiver"] == self._uid:
                direction = "<-"
                partner = entry["sender"]
            elif entry["sender"] == self._uid:
                direction = "->"
                partner = entry["receiver"]
                amount = -amount
            else:
                raise RuntimeError

            logs.append(
                "{}: {:=+6.2f} {} {} ({})".format(
                    time.strftime("%d.%m.%Y %H:%M:%S", entry["registered"].timetuple()),
                    amount,
                    direction,
                    user.BaseBotUser.get_name_from_uid(partner),
                    reason
                )
            )

        if len(logs) > 0:
            return "\n".join(logs)
        return ""

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

    @property
    def uid(self) -> int:
        return self._uid

    @property
    def valid(self) -> bool:
        return self._valid

    @property
    def history(self) -> typing.List[typing.Dict[str, typing.Any]]:
        return self._log
