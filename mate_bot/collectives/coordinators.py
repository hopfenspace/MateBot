"""
MateBot multi-user and multi-message coordinator classes
"""

import typing


from mate_bot.state.dbhelper import BackendHelper
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
