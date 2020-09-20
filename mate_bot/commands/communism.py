"""
MateBot command executor classes for /communism and its callback queries
"""

import uuid
import typing
import argparse
import datetime

import telegram.ext

from mate_bot import err
from mate_bot import state
from mate_bot.args.types import amount as amount_type
from mate_bot.args.actions import JoinAction
from mate_bot.commands.base import BaseCommand, BaseCallbackQuery, BaseInlineQuery, BaseInlineResult
from mate_bot.state import finders, MateBotUser, CommunityUser


COMMUNISM_ARGUMENTS = typing.Union[
    int,
    typing.Tuple[int, MateBotUser, telegram.Bot],
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

    :param arguments: either internal ID or tuple of arguments for creation
    :raises ValueError: when a supplied argument has an invalid value
    :raises TypeError: when a supplied argument has the wrong type
    :raises RuntimeError: when the internal collective ID points to a payment operation
    """

    _communistic = True

    _ALLOWED_COLUMNS = ["externals", "active"]

    def __init__(self, arguments: COMMUNISM_ARGUMENTS):

        self._price = 0
        self._fulfilled = None

        if isinstance(arguments, int):
            self._id = arguments
            self.update()
            if not self._communistic:
                raise RuntimeError("Remote record is no communism")

        elif isinstance(arguments, tuple):
            if len(arguments) == 3:

                communism_id, user, bot = arguments
                if not isinstance(communism_id, int):
                    raise TypeError("Expected int as first element")
                if not isinstance(user, MateBotUser):
                    raise TypeError("Expected MateBotUser object as second element")
                if not isinstance(bot, telegram.Bot):
                    raise TypeError("Expected telegram.Bot object as third element")

                self._id = communism_id
                self.update()

                forwarded = bot.send_message(
                    chat_id=user.tid,
                    text=self.get_markdown(),
                    reply_markup=self._gen_inline_keyboard(),
                    parse_mode="Markdown"
                )

                self.register_message(forwarded.chat_id, forwarded.message_id)

            elif len(arguments) == 4:

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
                raise ValueError("Expected three or four arguments for the tuple")

        else:
            raise TypeError("Expected int or tuple of arguments")

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

    def get_markdown(self) -> str:
        """
        Generate the full message text as markdown string

        :return: full message text as markdown string
        :rtype: str
        """

        markdown = f"*Communism by {self.creator.name}*\n\n{self._get_basic_representation()}"

        if self.active:
            markdown += "\n_The communism is currently active._"
        elif self._fulfilled is not None:
            if self._fulfilled:
                markdown += "\n_The communism was closed. All transactions have been processed._"
                if self._externals > 0:
                    markdown += (
                        f"\n\n{self._price / 100:.2f}€ must be collected from each "
                        f"external user by {self.creator.name}."
                    )
                else:
                    markdown += f"\n\nEvery joined user paid {self._price / 100:.2f}€."
            else:
                markdown += "\n_The communism was aborted. No transactions have been processed._"

        return markdown

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
                telegram.InlineKeyboardButton("FORWARD", switch_inline_query_current_chat = f"{self.get()} ")
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

    def accept(self, bot: telegram.Bot) -> bool:
        """
        Accept the collective operation, perform all transactions and update the message

        :param bot: Telegram Bot object
        :type bot: telegram.Bot
        :return: success of the operation
        :rtype: bool
        """

        if not self.close():
            return False

        self._fulfilled = True
        self.edit(bot)
        [self.unregister_message(c, m) for c, m in self.get_messages()]

        return True

    def cancel(self, bot: telegram.Bot) -> bool:
        """
        Cancel the current pending communism operation without fulfilling the transactions

        :param bot: Telegram Bot object
        :type bot: telegram.Bot
        :return: success of the operation
        :rtype: bool
        """

        if not self._abort():
            return False

        self._fulfilled = False
        self.edit(bot)
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


class CommunismCallbackQuery(BaseCallbackQuery):
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
            com.edit(update.callback_query.message.bot)

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
            com.edit(update.callback_query.message.bot)
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
            com.edit(update.callback_query.message.bot)
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

            if com.accept(update.callback_query.message.bot):
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

            if com.cancel(update.callback_query.message.bot):
                update.callback_query.answer(text="Okay, the communism was cancelled.")

    def run(self, update: telegram.Update) -> None:
        """
        Do not do anything (this class does not need run() to work)

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        pass


class CommunismInlineQuery(BaseInlineQuery):
    """
    User selection for forwarding communism messages to other users

    This feature is used to allow users to select a recipient from
    all known users in the database. This recipient will get the
    forwarded Communism message in a private chat message. To use
    this feature, the bot must be able to receive *all* updates
    for chosen inline query results. You may need to enable this
    updates via the @BotFather. Set the quota to 100%.
    """

    @staticmethod
    def get_uuid(communism_id: typing.Optional[int] = None, receiver: typing.Optional[int] = None) -> str:
        """
        Generate a random UUID or a string encoding information about forwarding communisms

        Note that both a communism ID and a receiver are necessary in order
        to generate the "UUID" that encodes the information to forward a communism.
        Note that the so-called UUID is not a valid RFC 4122 UUID. If at least one
        of the optional parameters are not present, a random UUID will be returned.
        That one, however, will be a valid RFC 4122 UUID created by the module `uuid`.

        :param communism_id: internal ID of the collective operation to be forwarded
        :type communism_id: typing.Optional[int]
        :param receiver: Telegram ID (Chat ID) of the recipient of the forwarded message
        :type receiver: typing.Optional[int]
        :return: string encoding information to forward communisms or a random UUID
        :rtype: str
        """

        if communism_id is None or receiver is None:
            return str(uuid.uuid4())

        now = int(datetime.datetime.now().timestamp())
        return f"{now}-{communism_id}-{receiver}"

    @staticmethod
    def get_result(
            heading: str,
            msg_text: str,
            communism_id: typing.Optional[int] = None,
            receiver: typing.Optional[int] = None,
            parse_mode: str = telegram.ParseMode.MARKDOWN
    ) -> telegram.InlineQueryResultArticle:
        """
        Build the InlineQueryResultArticle object that should be sent to the user as one option

        :param heading: heading of the inline result shown to the user
        :type heading: str
        :param msg_text:
        :type msg_text: str
        :param communism_id: internal ID of the collective operation to be forwarded
        :type communism_id: typing.Optional[int]
        :param receiver: Telegram ID (Chat ID) of the recipient of the forwarded message
        :type receiver: typing.Optional[int]
        :param parse_mode: parse mode specifier for the resulting message
        :type parse_mode: str
        :return:
        """

        return telegram.InlineQueryResultArticle(
            id = CommunismInlineQuery.get_uuid(communism_id, receiver),
            title = heading,
            input_message_content = telegram.InputTextMessageContent(
                message_text = msg_text,
                parse_mode = parse_mode,
                disable_web_page_preview = True
            )
        )

    def get_help(self) -> telegram.InlineQueryResultArticle:
        """
        Get the help option in the list of choices

        :return: inline query result choice for the help message
        :rtype: telegram.InlineQueryResultArticle
        """

        return self.get_result(
            "Help: What should I do here?",
            "*Help on using the inline mode of this bot*\n\n"
            "This bot enables users to forward communism and payment management "
            "messages to other users via a pretty comfortable inline search. "
            "Click on the button `FORWARD` of the message and then type the name, "
            "username or a part of it in the input field. There should already be "
            "a number besides the name of the bot. This number is required, forwarding "
            "does not work without this number. _Do not change it._ If you don't have "
            "a communism or payment message, you may try creating a new one. Use the "
            "commands /communism and /pay for this purpose, respectively. Use /help "
            "for a general help and an overview of other available commands."
        )

    def run(self, query: telegram.InlineQuery) -> None:
        """
        Search for a user in the database and allow the user to forward communisms

        :param query: inline query as part of an incoming Update
        :type query: telegram.InlineQuery
        :return: None
        """

        if len(query.query) == 0:
            return

        split = query.query.split(" ")

        try:
            comm_id = int(split[0])
            community = CommunityUser()

            users = []
            for word in split[1:]:
                if len(word) <= 1:
                    continue
                if word.startswith("@"):
                    word = word[1:]

                for target in finders.find_names_by_pattern(word):
                    user = finders.find_user_by_name(target)
                    if user is not None and user not in users:
                        if user.uid != community.uid:
                            users.append(user)

                for target in finders.find_usernames_by_pattern(word):
                    user = finders.find_user_by_username(target)
                    if user is not None and user not in users:
                        if user.uid != community.uid:
                            users.append(user)

            users.sort(key = lambda u: u.name.lower())

            answers = []
            for choice in users:
                answers.append(self.get_result(
                    f"{choice.name} ({choice.username})" if choice.username else choice.name,
                    f"I am forwarding this communism to {choice.name}...",
                    communism_id = comm_id,
                    receiver = choice.tid
                ))

            query.answer([self.get_help()] + answers)

        except (IndexError, ValueError):
            query.answer([self.get_help()])


class CommunismInlineResult(BaseInlineResult):
    """
    Communism message forwarding based on the inline query result reports

    This feature is used to forward communism management messages
    to other users. The receiver of the forwarded message had to be
    selected by another user using the inline query functionality.
    The `result ID` should store the encoded timestamp, receiver
    Telegram ID and internal ID of the collective operation.
    """

    def run(self, result: telegram.ChosenInlineResult, bot: telegram.Bot) -> None:
        """
        Forward a communism management message to other users

        :param result: report of the chosen inline query option as part of an incoming Update
        :type result: telegram.ChosenInlineResult
        :param bot: currently used Telegram Bot object
        :type bot: telegram.Bot
        :return: None
        """

        if result.result_id.count("-") == 3:
            return

        # No exceptions will be handled because errors here would mean
        # problems with the result ID which is generated by the bot itself
        ts, randint, comm_id, receiver = result.result_id.split("-")
        comm_id = int(comm_id)
        receiver = int(receiver)
        user = MateBotUser(MateBotUser.get_uid_from_tid(receiver))

        Communism((comm_id, user, bot))
