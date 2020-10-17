"""
MateBot multi-user and multi-message coordinator classes
"""

import typing


from mate_bot import err
from mate_bot.state.dbhelper import BackendHelper
from mate_bot.state.user import MateBotUser


class MessageCoordinator(BackendHelper):
    _id: int

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


class UserCoordinator(BackendHelper):
    _id: int

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
