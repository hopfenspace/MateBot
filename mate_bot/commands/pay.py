"""
MateBot command executor classes for /pay and its callback queries
"""

import typing
import logging

import telegram

from mate_bot.collectives.base import BaseCollective
from mate_bot.collectives.communism import Communism
from mate_bot.collectives.payment import Payment
from mate_bot.commands.base import BaseCommand, BaseCallbackQuery
from mate_bot.parsing.types import amount as amount_type
from mate_bot.parsing.actions import JoinAction
from mate_bot.parsing.util import Namespace
from mate_bot.state.user import MateBotUser


logger = logging.getLogger("commands")


class PayCommand(BaseCommand):
    """
    Command executor for /pay

    Note that the majority of the functionality is located in the query handler.
    """

    def __init__(self):
        super().__init__(
            "pay",
            "Use this command to create a payment request.\n\n"
            "When you want to get money from the community, a payment "
            "request needs to be created. It requires an amount and a description. "
            "The community members with vote permissions will then vote for or against "
            "your request to verify that your request is valid and legitimate. "
            "In case it's approved, the community will send the money to you.\n\n"
            "There are two subcommands that can be used. You can get your "
            "active request as a new message in the current chat by using show. "
            "You can stop your currently active payment request using stop.",
            "Use this command to create a payment request.<br /><br />"
            "When you want to get money from the community, a payment "
            "request needs to be created. It requires an amount and a description. "
            "The community members with vote permissions will then vote for or against "
            "your request to verify that your request is valid and legitimate. "
            "In case it's approved, the community will send the money to you.<br /><br />"
            "There are two subcommands that can be used. You can get your "
            "active request as a new message in the current chat by using <code>show</code>. "
            "You can stop your currently active payment request using <code>stop</code>."
        )

        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("reason", action=JoinAction, nargs="*")

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
            if Payment.has_user_active_collective(user):
                update.effective_message.reply_text("You already have a collective in progress.")
                return

            Payment((user, args.amount, args.reason, update.effective_message))
            return

        collective_id = BaseCollective.get_cid_from_active_creator(user)
        if collective_id is None:
            update.effective_message.reply_text("You don't have a collective in progress.")
            return

        if BaseCollective.get_type(collective_id):
            collective = Communism(collective_id)
            update.effective_message.reply_text(
                "Note that your currently active collective is no payment request, it's a communism."
            )
        else:
            collective = Payment(collective_id)

        if args.subcommand == "show":
            collective.show(update.effective_message)

        elif args.subcommand == "stop":
            collective.cancel(update.effective_message.bot)


class PayCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /pay
    """

    def __init__(self):
        super().__init__("pay", "^pay")

    def _get_payment(self, query: telegram.CallbackQuery) -> typing.Optional[Payment]:
        """
        Retrieve the Payment object based on the callback data

        :param query: incoming Telegram callback query with its attached data
        :type query: telegram.CallbackQuery
        :return: Payment object that handles the current collective
        :rtype: typing.Optional[Pay]
        """

        if self.data is None or self.data.strip() == "":
            query.answer("Empty stripped callback data!", show_alert=True)
            return

        try:
            vote, payment_id = self.data.split(" ")
        except IndexError:
            query.answer("Invalid callback data format!", show_alert=True)
            raise

        try:
            payment_id = int(payment_id)
        except ValueError:
            query.answer("Wrong payment ID format!", show_alert=True)
            raise

        try:
            pay = Payment(payment_id)
            if pay.active:
                return pay
            query.answer("The pay is not active anymore!")
        except IndexError:
            query.answer("The payment does not exist in the database!", show_alert=True)
            raise

    def run(self, update: telegram.Update) -> None:
        """
        Check and process the incoming callback query

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        payment = self._get_payment(update.callback_query)
        if payment is not None:
            user = MateBotUser(update.callback_query.from_user)
            if payment.creator == user:
                update.callback_query.answer(
                    "You can't vote on your own payment request.",
                    show_alert=True
                )
                return

            if not user.permission or user.external:
                update.callback_query.answer(
                    "You don't have the permission to vote on this payment request.",
                    show_alert=True
                )
                return

            if self.data.startswith("approve"):
                vote = True
            elif self.data.startswith("disapprove"):
                vote = False
            else:
                update.callback_query.answer("Invalid callback query data!", show_alert=True)
                raise ValueError(f"Invalid callback query data: '{self.data}'")

            success = payment.add_user(user, vote)
            if not success:
                update.callback_query.answer("You already voted on this payment request.")
                return

            update.callback_query.answer("You successfully voted on this payment request.")
            active, approved, disapproved = payment.close(update.callback_query.bot)
            status = None
            if not active:
                if len(approved) > len(disapproved):
                    status = "_The payment request has been accepted._"
                elif len(disapproved) > len(approved):
                    status = "_The payment request has been denied._"

            payment.edit_all_messages(
                payment.get_markdown(status),
                payment._get_inline_keyboard(),
                update.callback_query.bot
            )
