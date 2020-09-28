"""
MateBot command executor classes for /vouch
"""

import telegram

from mate_bot.commands.base import BaseCommand
from mate_bot.parsing import types
from mate_bot.parsing.util import Namespace
from mate_bot.state.user import MateBotUser


class VouchCommand(BaseCommand):
    """
    Command executor for /vouch
    """

    def __init__(self):
        super().__init__(
            "vouch",
            "Internal users can vouch for externals to allow them to use this bot. "
            "Otherwise, the possibilities would be very limited for security purposes."
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
        if owner.external:
            update.effective_message.reply_text("You can't perform this command.")
            return

        def reply(text: str) -> None:
            update.effective_message.reply_text(
                text,
                parse_mode="Markdown",
                reply_markup=telegram.InlineKeyboardMarkup([
                    [
                        telegram.InlineKeyboardButton(
                            "YES",
                            callback_data=f"vouch {args.command} accept"
                        ),
                        telegram.InlineKeyboardButton(
                            "NO",
                            callback_data=f"vouch {args.command} deny"
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
                    parse_mode = "Markdown"
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
                    f"**Do you really want to vouch for {args.user}?**\n\n"
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
                    f"**Do you really want to stop vouching for {args.user}?**\n\n"
                    "This will have some consequences:\n"
                    f"- {args.user.name} won't be able to perform commands that would change "
                    "the balance anymore (e.g. /send or consumption commands).\n"
                    f"- The balance of {args.user.name} will be set to `0`.\n"
                    f"- You will {'pay' if checkout < 0 else 'get'} {checkout / 100:.2f}€ "
                    f"{'to' if checkout < 0 else 'from'} the community."
                )
