#!/usr/bin/env python3

import typing
import argparse

import telegram

import state
from args import amount as amount_type, JoinAction
from .base import BaseCommand, BaseQuery


COMMUNISM_ARGUMENTS = typing.Union[int, typing.Tuple[state.MateBotUser, int, str]]


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

        if isinstance(arguments, int):
            self._id = arguments
            self.update()
            if not self._communistic:
                raise RuntimeError("Remote record is no communism")

        elif isinstance(arguments, tuple):
            if len(arguments) != 3:
                raise ValueError("Expected three arguments for the tuple")

            user, amount, reason = arguments
            if not isinstance(user, state.MateBotUser):
                raise TypeError("Expected MateBotUser object as first element")
            if not isinstance(amount, int):
                raise TypeError("Expected int object as second element")
            if not isinstance(reason, str):
                raise TypeError("Expected str object as third element")
            if len(reason) < 3:
                raise ValueError("Reason too short")

            self._creator = user.uid
            self._amount = amount
            self._description = reason
            self._externals = 0
            self._active = True

            self._create_new_record()

        else:
            raise TypeError("Expected int or tuple of arguments")

        """
        self.reason = reason
        self.members = [creator]
        self.message = None
        self.externs = 0

        prefix = "communism " + str(creator['id'])
        self.message_markup = telegram.InlineKeyboardMarkup([
            [
                telegram.InlineKeyboardButton("JOIN/LEAVE", callback_data=prefix + " join/leave"),
            ],
            [
                telegram.InlineKeyboardButton("EXTERN -", callback_data=prefix + " extern-"),
                telegram.InlineKeyboardButton("EXTERN +", callback_data=prefix + " extern+"),
            ],
            [
                telegram.InlineKeyboardButton("OK", callback_data=prefix + " ok"),
                telegram.InlineKeyboardButton("CANCEL", callback_data=prefix + " cancel"),
            ],
        ])
        """

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

    def amount_euro(self):
        return self.amount / float(100)

    def update_text(self):
        self.message.edit_text(str(self), reply_markup=self.message_markup)

    def __str__(self):
        return "Communism by {}\nAmount: {:.2f}€\nReason: {}\nExterns: {}\nCommunists: {}\n" \
            .format(self.creator['name'], self.amount_euro(), self.reason, self.externs,
                    user_list_to_string(self.members))


class CommunismCommand(BaseCommand):
    """
    Command executor for /communism

    Note that the majority of the functionality is located in the query handler.
    """

    def __init__(self):
        super().__init__("communism")
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

        sender = update.effective_message.from_user
        if sender.is_bot:
            return

        if state.MateBotUser.get_uid_from_tid(sender.id) is None:
            update.effective_message.reply_text("You need to /start first.")
            return

        user = state.MateBotUser(sender)
        if state.BaseCollective.has_user_active_collective(user):
            update.effective_message.reply_text("You already have a collective in progress.")
            return

        Communism((user, args.amount, args.reason))


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

    def toggle(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        pass

    def increase(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        pass

    def decrease(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        pass

    def accept(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        pass

    def cancel(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        pass


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
