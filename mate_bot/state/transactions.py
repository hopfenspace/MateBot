#!/usr/bin/env python3

import time
import typing

from . import user
from .dbhelper import execute as _execute


class InactiveTransaction:
    """
    Historic money transaction between two users (read-only data)
    """

    def __init__(self, src: user.BaseBotUser, dst: user.BaseBotUser, amount: int, reason: str = ""):
        """
        :param src: user that sends money to someone else
        :type src: user.BaseBotUser
        :param dst: user that receives money from someone else
        :type dst: user.BaseBotUser
        :param amount: money measured in Cent (must always be positive!)
        :type amount: int
        :param reason: optional description of / reason for the transactions
        :type reason: str
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
        self._reason = str(reason)
        self._committed = False

    def __bool__(self) -> bool:
        return True

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


class Transaction(InactiveTransaction):
    """
    Money transaction between two users
    """

    def __bool__(self) -> bool:
        return self._committed

    def commit(self) -> None:
        """
        Fulfill the transaction and store it in the database

        :raises RuntimeError: when amount is negative or zero
        :return: None
        """

        if self._amount < 0:
            raise RuntimeError("No negative transactions!")
        if self._amount == 0:
            raise RuntimeError("Empty transaction!")

        if not self._committed:
            _execute(
                "INSERT INTO transactions (fromuser, touser, amount, reason) VALUES (%s, %s, %s, %s)",
                (self._src.uid, self._dst.uid, self._amount, self._reason)
            )
            self._src.update()
            self._dst.update()
            self._src._update_record("balance", self._src.balance - self._amount)
            self._dst._update_record("balance", self._dst.balance + self._amount)
            self._committed = True

    @property
    def committed(self) -> bool:
        return self._committed


class TransactionLog:
    """
    Transaction history for a specific user based on the logs in the database
    """

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
            rows, self._log = _execute(
                "SELECT * FROM transactions WHERE fromuser=%s",
                (self._uid,)
            )
        elif self._mode > 0:
            rows, self._log = _execute(
                "SELECT * FROM transactions WHERE touser=%s",
                (self._uid,)
            )
        else:
            rows, self._log = _execute(
                "SELECT * FROM transactions WHERE fromuser=%s OR touser=%s",
                (self._uid, self._uid)
            )

        self._valid = True
        if rows == 0 and user.BaseBotUser.get_tid_from_uid(self._uid) is None:
            self._valid = False

    def to_string(self) -> str:
        """
        Return a pretty formatted version of the transaction log

        :return: str
        """

        logs = []
        for entry in self._log:
            amount = entry["amount"] / 100

            if entry["touser"] == self._uid:
                direction = "<-"
                partner = entry["fromuser"]
            elif entry["fromuser"] == self._uid:
                direction = "->"
                partner = entry["touser"]
                amount = -amount
            else:
                raise RuntimeError

            logs.append(
                "{}: {:=+6.2f} {} {} ({})".format(
                    time.strftime("%d.%m.%Y %H:%M:%S", entry["transtime"].timetuple()),
                    amount,
                    direction,
                    user.BaseBotUser.get_name_from_uid(partner),
                    entry["reason"]
                )
            )

        return "\n".join(logs)

    def to_json(self) -> typing.List[typing.Dict[str, typing.Union[int, str]]]:
        """
        Return a JSON-serializable list of transaction entries

        Note that the datetime objects will be converted to integers representing UNIX timestamps.

        :return: list
        """

        result = self._log[:]
        for entry in result:
            entry["transtime"] = int(entry["transtime"].timestamp())
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
