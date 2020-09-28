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

        self.parser.add_argument("user", nargs="?", type=types.user)

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

        if args.user is None:
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
                    "To change this, use `/vouch <username>`.",
                    parse_mode = "Markdown"
                )

            else:
                update.effective_message.reply_text(
                    "You currently vouch for the following "
                    f"user{'s' if len(debtors) != 1 else ''}: {debtors}",
                    parse_mode="Markdown"
                )

            return

        update.effective_message.reply_text("This feature is not implemented yet.")
