#!/usr/bin/env python3

from . import user


class Transaction:
    """
    Money transaction between two users
    """

    def __init__(self, src: user.MateBotUser, dst: user.MateBotUser, amount: int, reason: str = ""):
        """
        :param src: user that sends money to someone else
        :type src: user.MateBotUser
        :param dst: user that receives money from someone else
        :type dst: user.MateBotUser
        :param amount: money measured in Cent (must always be positive!)
        :type amount: int
        :param reason: optional description of / reason for the transactions
        :type reason: str
        """

        if amount <= 0:
            raise RuntimeError("No negative transactions!")

        self._src = src
        self._dst = dst
        self._amount = amount
        self._reason = reason

    def commit(self) -> None:
        """
        Fulfill the transaction and store it in the database

        :return: None
        """

    @property
    def src(self) -> user.MateBotUser:
        return self._src

    @property
    def dst(self) -> user.MateBotUser:
        return self._dst

    @property
    def amount(self) -> int:
        return self._amount

    @property
    def reason(self) -> str:
        return self._reason
