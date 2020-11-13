"""
MateBot payment requests to get money from the community upon community approval
"""

import typing
import logging

import telegram

from mate_bot.config import config
from mate_bot.collectives.base import BaseCollective, COLLECTIVE_ARGUMENTS
from mate_bot.state.transactions import LoggedTransaction
from mate_bot.state.user import CommunityUser, MateBotUser


logger = logging.getLogger("collectives")


class Payment(BaseCollective):
    """
    Payment class to get money from the community

    :param arguments: either internal ID or tuple of arguments for creation or forwarding
    :raises ValueError: when a supplied argument has an invalid value
    :raises TypeError: when a supplied argument has the wrong type
    :raises RuntimeError: when the collective ID doesn't match the class definition
        or when the class did not properly define its collective type using the class
        attribute ``_communistic`` (which is ``None`` by default and should be set properly)
    """

    _communistic = False

    _ALLOWED_COLUMNS = ["active"]

    def __init__(self, arguments: COLLECTIVE_ARGUMENTS):
        super().__init__(arguments, None)

    def get_votes(self) -> typing.Tuple[typing.List[MateBotUser], typing.List[MateBotUser]]:
        """
        Get the approving and disapproving voters as lists of MateBotUsers

        :return: the returned tuple contains a list of approving voters and disapproving voters each
        :rtype: typing.Tuple[typing.List[MateBotUser], typing.List[MateBotUser]]
        """

        approved = []
        disapproved = []

        for entry in self._get_remote_joined_record()[1]:
            if entry["collectives_users.id"] is None or entry["vote"] is None:
                continue
            user = MateBotUser(entry["users_id"])
            if entry["vote"]:
                approved.append(user)
            else:
                disapproved.append(user)

        return approved, disapproved

    def get_core_info(self) -> str:
        """
        Retrieve the basic information for the payment request's management message

        The returned string may be formatted using Markdown. The string
        should be suitable to be re-used inside :meth:`get_markdown`.

        :return: communism description message as pure text
        :rtype: str
        """

        approved, disapproved = self.get_votes()
        pro = ", ".join(map(lambda u: u.name, approved)) or "None"
        contra = ", ".join(map(lambda u: u.name, disapproved)) or "None"

        return (
            f"*Payment request by {self.creator.name}*\n"
            f"\nAmount: {self.amount / 100:.2f}€\nReason: {self.description}\n"
            f"\nApproved ({len(approved)}): {pro}"
            f"\nDisapproved ({len(disapproved)}): {contra}\n"
        )

    def get_markdown(self, status: typing.Optional[str] = None) -> str:
        """
        Generate the full message text as markdown string

        :param status: extended status information about the payment request (Markdown supported)
        :type status: typing.Optional[str]
        :return: full message text as markdown string
        :rtype: str
        """

        markdown = self.get_core_info()

        if status is not None:
            markdown += status
        elif self.active:
            markdown += "\n_The payment request is currently active._"
        else:
            markdown += "\n_The payment request has been closed._"

        return markdown

    def _get_inline_keyboard(self) -> telegram.InlineKeyboardMarkup:
        """
        Get the inline keyboard to control the payment operation

        :return: inline keyboard using callback data strings
        :rtype: telegram.InlineKeyboardMarkup
        """

        if not self.active:
            return telegram.InlineKeyboardMarkup([])

        def f(c):
            return f"pay {c} {self.get()}"

        return telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("APPROVE", callback_data=f("approve")),
                telegram.InlineKeyboardButton("DISAPPROVE", callback_data=f("disapprove")),
            ],
            [
                telegram.InlineKeyboardButton("FORWARD", switch_inline_query_current_chat=f"{self.get()} ")
            ]
        ])

    def cancel(self, bot: telegram.Bot) -> bool:
        """
        Cancel the current pending payment request without fulfilling the transaction

        Note that this method must not be executed by anyone else but the creator!

        :param bot: Telegram Bot object
        :type bot: telegram.Bot
        :return: success of the operation
        :rtype: bool
        """

        if not self.active:
            return False
        self.active = False
        self.edit_all_messages(self.get_markdown(), self._get_inline_keyboard(), bot)
        [self.unregister_message(c, m) for c, m in self.get_messages()]
        return True

    def show(self, message: telegram.Message) -> None:
        """
        Show the currently active payment request in the current chat

        :param message: command message that contains the request to show the payment message
        :type message: telegram.Message
        :return: None
        """

        reply = message.reply_text("Loading...")
        messages = self.get_messages(message.chat.id)

        for msg in messages:
            message.bot.edit_message_text(
                self.get_markdown(
                    "\n_This payment request management message is not active anymore. "
                    "A more recent message has been sent to the chat to replace this one._"
                ),
                chat_id=msg[0],
                message_id=msg[1],
                parse_mode="Markdown",
                reply_to_message_id=reply.message_id,
                reply_markup=telegram.InlineKeyboardMarkup([])
            )
            self.unregister_message(msg[0], msg[1])

        self.register_message(message.chat.id, reply.message_id)
        self.edit_all_messages(
            self.get_markdown(),
            self._get_inline_keyboard(),
            message.bot
        )

    def close(
            self,
            bot: typing.Optional[telegram.Bot] = None
    ) -> typing.Tuple[bool, typing.List[MateBotUser], typing.List[MateBotUser]]:
        """
        Check if the payment is fulfilled, then close it and perform the transactions

        The first returned value determines whether the payment request is still
        valid and open for further votes (``True``) or closed due to enough
        approving / disapproving votes (``False``). Use it to easily
        determine the status for the returned message to the user(s). The two
        lists of approving and disapproving users is just added for convenience.

        :param bot: optional Telegram Bot object that sends transaction logs to some chat(s)
        :type bot: typing.Optional[telegram.Bot]
        :return: a tuple containing the information whether the payment request is
            still open for further votes and the approving and disapproving user lists
        :rtype: typing.Tuple[bool, typing.List[MateBotUser], typing.List[MateBotUser]]
        """

        logger.debug(f"Attempting to close payment request {self.get()}...")
        approved, disapproved = self.get_votes()

        if len(approved) - len(disapproved) >= config["community"]["payment-consent"]:
            LoggedTransaction(
                CommunityUser(),
                self.creator,
                self.amount,
                f"pay: {self.description}",
                bot
            ).commit()

            self.active = False
            return False, approved, disapproved

        elif len(disapproved) - len(approved) >= config["community"]["payment-denial"]:
            self.active = False
            return False, approved, disapproved

        return True, approved, disapproved
