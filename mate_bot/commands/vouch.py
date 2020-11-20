"""
MateBot command executor classes for /vouch
"""

import logging

import telegram

from mate_bot.commands.base import BaseCommand, BaseCallbackQuery
from mate_bot.parsing import types
from mate_bot.parsing.util import Namespace
from mate_bot.state.user import MateBotUser
from mate_bot.state.transactions import Transaction


logger = logging.getLogger("commands")


class VouchCommand(BaseCommand):
    """
    Command executor for /vouch
    """

    def __init__(self):
        super().__init__(
            "vouch",
            "Use this command to vouch for other users.\n\n"
            "The possible interactions with this bot are pretty limited for external "
            "people for security purposes. If you intend to use this bot, you can ask an "
            "internal user to vouch for you. Doing so gives you the necessary permissions.\n\n"
            "On the other hand, internal users can vouch for externals to allow them to use "
            "this bot. You should note that you will be held responsible in case the user "
            "you are vouching for can't pay possible debts for whatever reason. If the "
            "community decides to disable the external user's account, you have to pay "
            "remaining debts, if there are any. However, you would also get the balance in "
            "case it's positive. After all, you are responsible to deal with the external user."
            "Use this command to vouch for other users.<br /><br />",
            "The possible interactions with this bot are pretty limited for external "
            "people for security purposes. If you intend to use this bot, you can ask an "
            "internal user to vouch for you. Doing so gives you the necessary permissions.<br /><br />"
            "On the other hand, internal users can vouch for externals to allow them to use "
            "this bot. You should note that you will be held responsible in case the user "
            "you are vouching for can't pay possible debts for whatever reason. If the "
            "community decides to disable the external user's account, you have to pay "
            "remaining debts, if there are any. However, you would also get the balance in "
            "case it's positive. After all, you are responsible to deal with the external user."
        )

        p = self.parser.new_usage()
        p.add_argument(
            "command",
            choices=("add", "remove"),
            type=lambda x: str(x).lower()
        )
        p.add_argument(
            "user",
            type=types.user
        )

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        owner = MateBotUser(update.effective_message.from_user)
        if not self.ensure_permissions(owner, 2, update.effective_message):
            return

        def reply(text: str) -> None:
            update.effective_message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=telegram.InlineKeyboardMarkup([
                    [
                        telegram.InlineKeyboardButton(
                            "YES",
                            callback_data=f"vouch {args.command} {args.user.uid} {owner.uid} accept"
                        ),
                        telegram.InlineKeyboardButton(
                            "NO",
                            callback_data=f"vouch {args.command} {args.user.uid} {owner.uid} deny"
                        )
                    ]
                ])
            )

        if args.command is None:
            debtors = ", ".join(map(
                lambda u: f"{u.name} ({u.username})" if u.username else u.name,
                map(
                    lambda i: MateBotUser(i),
                    owner.debtors
                )
            ))

            if len(debtors) == 0:
                update.effective_message.reply_text(
                    "You don't vouch for any external user at the moment. "
                    "To change this, use `/vouch add|remove <username>`.",
                    parse_mode="Markdown"
                )

            else:
                update.effective_message.reply_text(
                    "You currently vouch for the following "
                    f"user{'s' if len(debtors) != 1 else ''}: {debtors}",
                    parse_mode="Markdown"
                )

        elif not args.user.external:
            update.effective_message.reply_text(
                f"This user is not external. Therefore, you can't vouch for {args.user}."
            )

        elif args.command == "add":
            if args.user.creditor == owner.uid:
                update.effective_message.reply_text(
                    f"You already vouch for {args.user.name}. If you want to "
                    "stop this, use the command `/vouch remove "
                    f"{args.user.username if args.user.username else '<username>'}`.",
                    parse_mode="Markdown"
                )

            elif args.user.creditor is not None:
                update.effective_message.reply_text(
                    "Someone else is already vouching for this user. "
                    f"Therefore, you can't vouch for {args.user.name}."
                )

            else:
                reply(
                    f"*Do you really want to vouch for {args.user}?*\n\n"
                    "This will have some consequences:\n"
                    "- The external user will become able to perform operations that change "
                    "the balance like /send or consumption commands.\n"
                    f"- You **must pay all debts** to the community when {args.user.name} "
                    "leaves the community for a longer period or forever or in case you stop "
                    f"vouching for {args.user.name}. On the other side, you will "
                    "get all the virtual money the user had when there's some.\n\n"
                    f"We encourage you to talk to {args.user.name} regularly or use /balance to "
                    "check the balance (this is currently possible for all registered users)."
                )

        elif args.command == "remove":
            if args.user.creditor is None:
                update.effective_message.reply_text(
                    "No one is vouching for this user yet. Therefore, you "
                    f"can't remove {args.user.name} from your list of debtors."
                )

            elif args.user.creditor != owner.uid:
                update.effective_message.reply_text(
                    "You don't vouch for this user, but someone else does. Therefore, you "
                    f"can't remove {args.user.name} from your list of debtors."
                )

            else:
                checkout = args.user.balance
                reply(
                    f"*Do you really want to stop vouching for {args.user}?*\n\n"
                    "This will have some consequences:\n"
                    f"- {args.user.name} won't be able to perform commands that would change "
                    "the balance anymore (e.g. /send or consumption commands).\n"
                    f"- The balance of {args.user.name} will be set to `0`.\n"
                    f"- You will {'pay' if checkout < 0 else 'get'} {checkout / 100:.2f}€ "
                    f"{'to' if checkout < 0 else 'from'} {args.user.name}."
                )


class VouchCallbackQuery(BaseCallbackQuery):
    """
    Callback query executor for /vouch
    """

    def __init__(self):
        super().__init__("vouch", "^vouch")

    def run(self, update: telegram.Update) -> None:
        """
        Process or abort the query to add or remove the debtor user

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        try:
            cmd, debtor, creditor, confirmation = self.data.split(" ")
            creditor = MateBotUser(int(creditor))
            debtor = MateBotUser(int(debtor))

            sender = MateBotUser(update.callback_query.from_user)
            if sender != creditor:
                update.callback_query.answer(f"Only the creator of this query can {confirmation} it!")
                return

            if confirmation == "deny":
                text = "_You aborted this operation._"

            elif confirmation == "accept":
                if cmd == "add":
                    text = f"_You now vouch for {debtor.name}._"
                    debtor.creditor = creditor

                elif cmd == "remove":
                    reason = f"vouch: {creditor.name} stopped vouching for {debtor.name}"
                    text = f"_Success. {debtor.name} has no active creditor anymore._"
                    if debtor.balance > 0:
                        text += f"\n_You received {debtor.balance / 100 :.2f}€ from {debtor.name}._"
                        Transaction(debtor, creditor, debtor.balance, reason).commit()
                    elif debtor.balance < 0:
                        text += f"\n_You sent {debtor.balance / 100 :.2f}€ to {debtor.name}._"
                        Transaction(creditor, debtor, debtor.balance, reason).commit()
                    debtor.creditor = None

                else:
                    raise ValueError("Invalid query data")

            else:
                raise ValueError("Invalid query data")

            update.callback_query.message.reply_text(
                text,
                parse_mode="Markdown",
                reply_to_message=update.callback_query.message
            )

            update.callback_query.message.edit_text(
                update.callback_query.message.text_markdown_v2,
                parse_mode="MarkdownV2"
            )

        except (IndexError, ValueError, TypeError, RuntimeError):
            update.callback_query.answer(
                text="There was an error processing your request!",
                show_alert=True
            )
            raise
