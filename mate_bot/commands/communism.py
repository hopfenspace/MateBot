"""
MateBot command executor classes for /communism and its callback queries
"""

import typing
import logging

import telegram.ext

from mate_bot import err
from mate_bot.collectives.base import BaseCollective
from mate_bot.collectives.communism import Communism
from mate_bot.collectives.payment import Payment
from mate_bot.parsing.types import amount as amount_type
from mate_bot.parsing.actions import JoinAction
from mate_bot.parsing.util import Namespace
from mate_bot.commands.base import BaseCommand, BaseCallbackQuery
from mate_bot.state.user import MateBotUser


logger = logging.getLogger("commands")


class CommunismCommand(BaseCommand):
    """
    Command executor for /communism

    Note that the majority of the functionality is located in the query handler.
    """

    def __init__(self):
        super().__init__(
            "communism",
            "Use this command to start a communism.\n\n"
            "When you pay for something that is used or otherwise consumed by a bigger "
            "group of people, you can open a communism for it to get your money back.\n\n"
            "When you use this command, you specify a reason and the price. The others "
            "can join afterwards (you might need to remember them). Users without "
            "Telegram can also join by adding an 'external'. You have to collect the "
            "money from each external by yourself. After everyone has joined, "
            "you close the communism to calculate and evenly distribute the price.\n\n"
            "There are two subcommands that can be used. You can get your "
            "active communism as a new message in the current chat by using show. "
            "You can stop your currently active communism using stop.",
            "Use this command to start a communism.\n\n"
            "When you pay for something that is used or otherwise consumed by a bigger "
            "group of people, you can open a communism for it to get your money back.\n\n"
            "When you use this command, you specify a reason and the price. The others "
            "can join afterwards (you might need to remember them). Users without "
            "Telegram can also join by adding an 'external'. You have to collect the "
            "money from each external by yourself. After everyone has joined, "
            "you close the communism to calculate and evenly distribute the price.\n\n"
            "There are two subcommands that can be used. You can get your "
            "active communism as a new message in the current chat by using <code>show</code>. "
            "You can stop your currently active communism using <code>stop</code>.",
        )

        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", nargs="+", action=JoinAction)

        self.parser.new_usage().add_argument(
            "subcommand",
            choices=("stop", "show"),
            type=lambda x: str(x).lower()
        )

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = MateBotUser(update.effective_message.from_user)
        if not self.ensure_permissions(user, 1, update.effective_message):
            return

        if args.subcommand is None:
            if BaseCollective.has_user_active_collective(user):
                update.effective_message.reply_text("You already have a collective in progress.")
                return

            Communism((user, args.amount, args.reason, update.effective_message))
            return

        collective_id = BaseCollective.get_cid_from_active_creator(user)
        if collective_id is None:
            update.effective_message.reply_text("You don't have a collective in progress.")
            return

        if BaseCollective.get_type(collective_id):
            collective = Communism(collective_id)
        else:
            collective = Payment(collective_id)
            update.effective_message.reply_text(
                "Note that your currently active collective is no communism, it's a payment request."
            )

        if args.subcommand == "show":
            collective.show(update.effective_message)

        elif args.subcommand == "stop":
            collective.cancel(update.effective_message.bot)


class CommunismCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /communism
    """

    def __init__(self):
        super().__init__(
            "communism",
            "^communism",
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
            user = MateBotUser(update.callback_query.from_user)
            previous_member = com.is_participating(user)[0]
            com.toggle_user(user)
            com.edit_all_messages(
                com.get_markdown(),
                com._get_inline_keyboard(),
                update.effective_message.bot
            )

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
            if com.creator != MateBotUser(update.callback_query.from_user):
                update.callback_query.answer(
                    text="You can't increase the external counter. You are not the creator.",
                    show_alert=True
                )
                return

            com.externals += 1
            com.edit_all_messages(
                com.get_markdown(),
                com._get_inline_keyboard(),
                update.effective_message.bot
            )
            update.callback_query.answer("Okay, incremented.")

    def decrease(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != MateBotUser(update.callback_query.from_user):
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
            com.edit_all_messages(
                com.get_markdown(),
                com._get_inline_keyboard(),
                update.effective_message.bot
            )
            update.callback_query.answer("Okay, decremented.")

    def accept(self, update: telegram.Update) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        com = self.get_communism(update.callback_query)
        if com is not None:
            if com.creator != MateBotUser(update.callback_query.from_user):
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
            if com.creator != MateBotUser(update.callback_query.from_user):
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
