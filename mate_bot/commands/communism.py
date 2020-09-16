"""
MateBot command executor classes for /communism and its callback queries
"""

import typing
import argparse

import telegram

from mate_bot import err
from mate_bot import state
from mate_bot.args.types import amount as amount_type
from mate_bot.args.actions import JoinAction
from mate_bot.commands.base import BaseCommand, BaseQuery


COMMUNISM_ARGUMENTS = typing.Union[
    int,
    typing.Tuple[state.MateBotUser, int, str, telegram.Message]
]


class Communism(state.BaseCollective):
    """
    Communism class to collect money from various other persons

    The constructor of this class accepts two different argument
    types. You can specify a single integer to get the Communism object
    that matches a remote record where the integer is the internal
    collectives ID. Alternatively, you can specify a tuple containing
    three objects: the creator of the new Communism as a MateBotUser
    object, the amount of the communism as integer measured in Cent
    and the description of the communism as string. While being optional
    in the database, you have to specify at least three chars as reason.
    """

    _communistic = True

    _ALLOWED_COLUMNS = ["externals", "active"]

    def __init__(self, arguments: COMMUNISM_ARGUMENTS):
        """
        :param arguments: either internal ID or tuple of arguments for creation
        :type arguments: typing.Union[int, typing.Tuple[state.MateBotUser, int, str]]
        :raises ValueError: when a supplied argument has an invalid value
        :raises TypeError: when a supplied argument has the wrong type
        :raises RuntimeError: when the internal collective ID points to a payment operation
        """

        self._price = 0
        self._fulfilled = None

        if isinstance(arguments, int):
            self._id = arguments
            self.update()
            if not self._communistic:
                raise RuntimeError("Remote record is no communism")

        elif isinstance(arguments, tuple):
            if len(arguments) != 4:
                raise ValueError("Expected four arguments for the tuple")

            user, amount, reason, message = arguments
            if not isinstance(user, state.MateBotUser):
                raise TypeError("Expected MateBotUser object as first element")
            if not isinstance(amount, int):
                raise TypeError("Expected int object as second element")
            if not isinstance(reason, str):
                raise TypeError("Expected str object as third element")
            if not isinstance(message, telegram.Message):
                raise TypeError("Expected telegram.Message as fourth element")

            self._creator = user.uid
            self._amount = amount
            self._description = reason
            self._externals = 0
            self._active = True

            self._create_new_record()
            self.add_user(user)

            reply = message.reply_markdown(self.get_markdown(), reply_markup=self._gen_inline_keyboard())
            self.register_message(reply.chat_id, reply.message_id)

        else:
            raise TypeError("Expected int or tuple of arguments")

    def __str__(self) -> str:
        message = self._get_basic_representation()

        if self.active:
            message += "\n_The communism is currently active._"
        else:
            message += "\n_The communism is closed.\nAll transactions have been processed._\n"
            if self._externals > 0:
                message += (
                    f"\n{self._price / 100:.2f}€ must be collected "
                    f"from each\nexternal user by {self.creator.name}."
                )

        return message

    def _get_basic_representation(self) -> str:
        """
        Retrieve the core information for the communism description message

        :return: communism description message as pure text
        :rtype: str
        """

        usernames = ', '.join(self.get_users_names())
        if usernames == "":
            usernames = "None"

        return (
            f"Reason: {self.description}\n"
            f"Amount: {self.amount / 100 :.2f}€\n"
            f"Externals: {self.externals}\n"
            f"Joined users: {usernames}\n"
        )

    def get_markdown(self, status: str = "") -> str:
        """
        Generate the full message text as markdown string

        :param status: additional status information at the bottom of the message
        :type status: str
        :return: full message text as markdown string
        :rtype: str
        """

        status = status.replace("\n", "_\n_")
        return (
            f"*Communism by {self.creator.name}*\n\n{self._get_basic_representation()}\n"
            f"_{status}_"
        )

    def _gen_inline_keyboard(self) -> telegram.InlineKeyboardMarkup:
        """
        Generate the inline keyboard to control the communism

        :return: inline keyboard using callback data strings
        :rtype: telegram.InlineKeyboardMarkup
        """

        if not self.active:
            return telegram.InlineKeyboardMarkup([])

        def f(c):
            return f"communism {c} {self.get()}"

        return telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("JOIN / LEAVE", callback_data = f("toggle")),
            ],
            [
                telegram.InlineKeyboardButton("EXTERNALS +", callback_data = f("increase")),
                telegram.InlineKeyboardButton("EXTERNALS -", callback_data = f("decrease")),
            ],
            [
                telegram.InlineKeyboardButton("ACCEPT", callback_data = f("accept")),
                telegram.InlineKeyboardButton("CANCEL", callback_data = f("cancel")),
            ]
        ])

    def edit(self, bot: telegram.Bot) -> None:
        """
        Edit the content of the communism messages in all chats

        :param bot: Telegram Bot object
        :type bot: telegram.Bot
        :return: None
        """

        for c, m in self.get_messages():
            bot.edit_message_text(
                self.get_markdown(),
                chat_id=c,
                message_id=m,
                reply_markup=self._gen_inline_keyboard(),
                parse_mode="Markdown"
            )

    def close(self) -> bool:
        """
        Close the collective operation and perform all transactions

        :return: success of the operation
        :rtype: bool
        """

        users = self.get_users()
        participants = self.externals + len(users)
        if participants == 0:
            return False

        self._price = self.amount // participants

        # Avoiding too small amounts by letting everyone pay one Cent more
        if self.amount % participants:
            self._price += 1

        for member in users:
            if member == self.creator:
                continue

            state.Transaction(
                member,
                self.creator,
                self._price,
                f"communism: {self.description} ({self.get()})"
            ).commit()

        self.active = False
        return True

    def accept(self, message: telegram.Message) -> bool:
        """
        Accept the collective operation, perform all transactions and update the message

        :param message: Telegram message handling the communism interactions
        :type message: telegram.Message
        :return: success of the operation
        :rtype: bool
        """

        if not self.close():
            return False

        self._fulfilled = True
        self.edit(message.bot)
        [self.unregister_message(c, m) for c, m in self.get_messages()]

        return True

    def cancel(self, message: telegram.Message) -> bool:
        """
        Cancel the current pending communism operation without fulfilling the transactions

        :param message: Telegram message handling the communism interactions
        :type message: telegram.Message
        :return: success of the operation
        :rtype: bool
        """

        if not self._abort():
            return False

        self._fulfilled = False
        self.edit(message.bot)
        [self.unregister_message(c, m) for c, m in self.get_messages()]

        return True

    @property
    def externals(self) -> int:
        """
        Get and set the number of external users for the communism
        """

        return self._externals

    @externals.setter
    def externals(self, new: int) -> None:
        if not isinstance(new, int):
            raise TypeError("Expected integer")
        if new < 0:
            raise ValueError("External user count can't be negative")
        if abs(self._externals - new) > 1:
            raise ValueError("External count must be increased or decreased by 1")

        self._externals = new
        self._set_remote_value("externals", new)


class CommunismCommand(BaseCommand):
    """
    Command executor for /communism

    Note that the majority of the functionality is located in the query handler.
    """

    def __init__(self):
        super().__init__("communism", "Use this command to start a communism.\n\n"
                                      "When you pay for something you and others "
                                      "consume, you can make a communism for it to get "
                                      "your money back.\n\n"
                                      "You use this command specifying a reason "
                                      "and how much it costs you. Then others can "
                                      "join (you might need to remember them) "
                                      "and after everyone has joined, "
                                      "you can close it. "
                                      "Then the price is evenly distributed "
                                      "between everyone who has joined.")
        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", nargs="+", action=JoinAction)

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = state.MateBotUser(update.effective_message.from_user)
        if state.BaseCollective.has_user_active_collective(user):
            update.effective_message.reply_text("You already have a collective in progress.")
            return

        Communism((user, args.amount, args.reason, update.effective_message))


class CommunismQuery(BaseQuery):
    """
    Callback query executor for /communism
    """

    def __init__(self):
        super().__init__(
            "communism",
            {
                "toggle": self.toggle,
                "increase": self.increase,
                "decrease": self.decrease,
                "accept": self.accept,
                "cancel": self.cancel
            }
        )

    def _get_communism(self) -> Communism:
        """
        Retrieve the Communism object based on the callback data

        :return: Communism object that handles the current collective
        :rtype: Communism
        :raises err.CallbackError: when something went wrong
        """

        if self.data is None or self.data == "":
            raise err.CallbackError("Empty stripped callback data")

        communism_id = self.data.split(" ")[-1]
        try:
            communism_id = int(communism_id)
        except ValueError as exc:
            raise err.CallbackError("Wrong communism ID format", exc)

        try:
            return Communism(communism_id)
        except IndexError as exc:
            raise err.CallbackError("The collective does not exist in the database", exc)
        except (TypeError, RuntimeError) as exc:
            raise err.CallbackError("The collective has the wrong remote type", exc)

    def get_communism(self, query: telegram.CallbackQuery) -> typing.Optional[Communism]:
        """
        Retrieve the Communism object based on the callback data

        By convention, everything after the last space symbol
        should be interpreted as communism ID. If some error occurs
        while trying to get the Communism object, an alert message
        will be shown to the user and an exception will be raised.

        :param query: incoming Telegram callback query with its attached data
        :type query: telegram.CallbackQuery
        :return: Communism object that handles the current collective
        :rtype: typing.Optional[Communism]
        :raises err.CallbackError: when something went wrong
        """

        try:
            com = self._get_communism()
            if com.active:
                return com
            query.answer("The communism is not active anymore!")

        except err.CallbackError:
            query.answer(
                text="Your requested action was not performed! Please try again later.",
                show_alert=True
            )
            raise

    def toggle(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            user = state.MateBotUser(update.callback_query.from_user)
            previous_member = com.is_participating(user)[0]
            com.toggle_user(user)
            com.edit(update.callback_query.message)

            if previous_member:
                update.callback_query.answer("Okay, you were removed.")
            else:
                update.callback_query.answer("Okay, you were added.")

    def increase(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != state.MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't increase the external counter. You are not the creator.",
                    show_alert=True
                )
                return

            com.externals += 1
            com.edit(update.callback_query.message)
            update.callback_query.answer("Okay, incremented.")

    def decrease(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != state.MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't decrease the external counter. You are not the creator.",
                    show_alert=True
                )
                return

            if com.externals == 0:
                update.callback_query.answer(
                    text="The externals counter can't be negative!",
                    show_alert=True
                )
                return

            com.externals -= 1
            com.edit(update.callback_query.message)
            update.callback_query.answer("Okay, decremented.")

    def accept(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != state.MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't accept this communism. You are not the creator.",
                    show_alert=True
                )
                return

            if com.accept(update.callback_query.message):
                update.callback_query.answer(text="The communism has been closed successfully.")
            else:
                update.callback_query.answer(
                    text="The communism was not accepted. Are there any members?",
                    show_alert=True
                )

    def cancel(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != state.MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't close this communism. You are not the creator.",
                    show_alert=True
                )
                return

            if com.cancel(update.callback_query.message):
                update.callback_query.answer(text="Okay, the communism was cancelled.")

    def run(self, update: telegram.Update) -> None:
        """
        Do not do anything (this class does not need run() to work)

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        pass
