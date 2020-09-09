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

            message.reply_markdown(str(self), reply_markup=self._gen_inline_keyboard())

        else:
            raise TypeError("Expected int or tuple of arguments")

    def __str__(self) -> str:
        usernames = ', '.join(self.get_users_names())
        if usernames == "":
            usernames = "None"
        return (
            f"*Communism by {self.creator.name}*\n\n"
            f"Reason: {self.description}\n"
            f"Amount: {self.amount / 100 :.2f}\n"
            f"Externals: {self.externals}\n"
            f"Joined users: {usernames}\n"
            f"Currently active: *{self.active}*"
        )

    def _gen_inline_keyboard(self) -> telegram.InlineKeyboardMarkup:
        """
        Generate the inline keyboard to control the communism

        :return: inline keyboard using callback data strings
        :rtype: telegram.InlineKeyboardMarkup
        """

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

    def edit(self, message: telegram.Message) -> None:
        """
        Edit the content of the "main" message that sends the callback queries

        :param message: Telegram message handling the communism interactions
        :type message: telegram.Message
        :return: None
        """

        message.edit_text(
            str(self),
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
        self._price = self.amount // participants

        # Avoiding too small amounts by letting everyone pay one Cent more
        if self.amount % participants:
            self._price += 1

        for member in users:
            state.Transaction(
                member,
                self.creator,
                self._price,
                f"communism: {self.description} ({self.get()})"
            ).commit()

        self.active = False

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
        super().__init__("communism", "")
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
            com.toggle_user(state.MateBotUser(update.callback_query.from_user))
            com.edit(update.callback_query.message)

    def increase(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            com.externals += 1
            com.edit(update.callback_query.message)

    def decrease(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            com.externals -= 1
            com.edit(update.callback_query.message)

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

            if com.close():
                update.callback_query.answer(text="The communism has been closed successfully.")
                com.edit(update.callback_query.message)

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

    def run(self, update: telegram.Update) -> None:
        """
        Do not do anything (this class does not need run() to work)

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        pass


"""
def communism_query(_, update):
    sender, selected_communism, cmd, sender_id, action = get_data_from_query(update, communisms)

    members = selected_communism.members
    is_admin = sender == selected_communism.creator

    if action == "join/leave":
        if sender in members:
            members.remove(sender)
        else:
            members.append(sender)

        if len(members) == 0:
            del communisms[split[1]]
            selected_communism.message.edit_text("Everyone left, the communism died")
        else:
            selected_communism.update_text()
    elif is_admin and action == "ok":
        count = len(members) + selected_communism.externs
        amount = selected_communism.amount // count

        # if the amount can't be split equally everyone pays 1 cent more
        if selected_communism.amount % count != 0:
            amount = amount + 1

        reason = "communism by " + selected_communism.creator['name']
        for member in members:
            create_transaction(member, -amount, reason)

        payout = selected_communism.amount - selected_communism.externs * amount
        create_transaction(selected_communism.creator, payout, reason)
        del communisms[split[1]]

        creator = selected_communism.creator['name']
        amountf = amount / float(100)
        text = "Communism by {}\n{} paid {:.2f}\n{} received {:.2f}\n{:.2f} has to be collected from {} externs\nDescription: {}" \
            .format(creator, user_list_to_string(selected_communism.members), amountf,
                    creator, payout / float(100), amountf, selected_communism.externs, selected_communism.reason)
        selected_communism.message.edit_text(text)

    elif is_admin and action == "cancel":
        del communisms[sender_id]
        selected_communism.message.edit_text("Communism canceled")

    elif is_admin and action == "extern-":
        if selected_communism.externs > 0:
            selected_communism.externs -= 1
            selected_communism.update_text()
        else:
            update.message.reply_text("Cannot reduce externs below zero")

    elif is_admin and action == "extern+":
        selected_communism.externs += 1
        selected_communism.update_text()
"""
