#!/usr/bin/env python3

from . import user


class Transaction:
    """
    Money transaction between two users
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
