"""
MateBot command executor classes for /send
"""

import logging

import telegram

from mate_bot.parsing.types import amount as amount_type
from mate_bot.parsing.types import user as user_type
from mate_bot.parsing.util import Namespace
from mate_bot.commands.base import BaseCallbackQuery, BaseCommand
from mate_bot.state.user import MateBotUser
from mate_bot.state.transactions import Transaction


logger = logging.getLogger("commands")


class SendCommand(BaseCommand):
    """
    Command executor for /send
    """

    def __init__(self):
        super().__init__("send", "Send money to another user.")
        self.parser.add_argument("amount", type=amount_type)
        self.parser.add_argument("receiver", type=user_type)
        self.parser.add_argument("reason", default="<no description>", nargs="*")

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        sender = MateBotUser(update.effective_message.from_user)
        if isinstance(args.reason, list):
            reason = "send: " + " ".join(args.reason)
        else:
            reason = "send: " + args.reason

        if sender == args.receiver:
            update.effective_message.reply_text("You can't send money to yourself!")
            return

        def e(variant: str) -> str:
            return f"send {variant} {args.amount} {sender.uid} {args.receiver.uid}"

        update.effective_message.reply_text(
            f"Do you want to send {args.amount / 100 :.2f}€ to {str(args.receiver)}?"
            f"\nDescription: `{reason}`",
            reply_markup = telegram.InlineKeyboardMarkup([
                [
                    telegram.InlineKeyboardButton("CONFIRM", callback_data = e("confirm")),
                    telegram.InlineKeyboardButton("ABORT", callback_data = e("abort"))
                ]
            ]),
            parse_mode = "Markdown"
        )


class SendCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /send
    """

    def __init__(self):
        super().__init__("send")

    def run(self, update: telegram.Update) -> None:
        """
        Process or abort transaction requests based on incoming callback queries

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        try:
            variant, amount, original_sender, receiver = self.data.split(" ")
            amount = int(amount)
            receiver = MateBotUser(int(receiver))
            original_sender = MateBotUser(int(original_sender))

            if variant == "confirm":
                confirmation = True
            elif variant == "abort":
                confirmation = False
            else:
                raise ValueError(f"Invalid confirmation setting: '{variant}'")

            sender = MateBotUser(update.callback_query.from_user)
            if sender != original_sender:
                update.callback_query.answer(f"Only the creator of this transaction can {variant} it!")
                return

            reason = None
            for entity in update.callback_query.message.parse_entities():
                if entity.type == "code":
                    if reason is None:
                        reason = update.callback_query.message.parse_entity(entity)
                    else:
                        raise RuntimeError("Multiple reason definitions")

            if reason is None:
                raise RuntimeError("Unknown reason while confirming a Transaction")

            if confirmation:
                trans = Transaction(sender, receiver, amount, reason)
                trans.commit()

                update.callback_query.message.edit_text(
                    f"Okay, you sent {amount / 100 :.2f}€ to {str(receiver)}",
                    reply_markup = telegram.InlineKeyboardMarkup([])
                )

            else:
                update.callback_query.message.edit_text(
                    "You aborted the operation. No money has been sent.",
                    reply_markup = telegram.InlineKeyboardMarkup([])
                )

        except (IndexError, ValueError, TypeError, RuntimeError):
            update.callback_query.answer(
                text="There was an error processing your request!",
                show_alert=True
            )
            update.callback_query.message.edit_text(
                "There was an error processing this request. No money has been sent.",
                reply_markup = telegram.InlineKeyboardMarkup([])
            )
            raise
