"""
MateBot command executor classes for /history
"""

import json
import logging
import tempfile

import telegram

from mate_bot.state.user import MateBotUser
from mate_bot.state.transactions import TransactionLog
from mate_bot.parsing.types import natural as natural_type
from mate_bot.parsing.util import Namespace
from mate_bot.commands.base import BaseCommand


logger = logging.getLogger("commands")


class HistoryCommand(BaseCommand):
    """
    Command executor for /history
    """

    def __init__(self):
        super().__init__(
            "history",
            "Use this command to get an overview of your transactions.\n\n"
            "You can specify the number of most recent transactions (default "
            "10) which will be returned by the bot. Using a huge number will "
            "just print all your transactions, maybe in multiple messages.\n\n"
            "You could also export the whole history of your personal transactions "
            "as downloadable file. Currently supported formats are `csv` and `json`. "
            "Just add one of those two format specifiers after the command. Note "
            "that this variant is restricted to your personal chat with the bot."
        )

        self.parser.add_argument(
            "length",
            nargs="?",
            default=10,
            type=natural_type
        )
        self.parser.new_usage().add_argument(
            "export",
            nargs="?",
            type=lambda x: str(x).lower(),
            choices=("json", "csv")
        )

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.export is None:
            self._handle_report(args, update)
        else:
            self._handle_export(args, update)

    @staticmethod
    def _handle_export(args: Namespace, update: telegram.Update) -> None:
        """
        Handle the request to export the full transaction log of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if update.effective_chat.type != update.effective_chat.PRIVATE:
            update.effective_message.reply_text("This command can only be used in private chat.")
            return

        user = MateBotUser(update.effective_message.from_user)

        if args.export == "json":

            logs = TransactionLog(user).to_json()
            if len(logs) == 0:
                update.effective_message.reply_text("You don't have any registered transactions yet.")
                return

            with tempfile.TemporaryFile(mode="w+b") as file:
                file.write(json.dumps(logs, indent=4).encode("UTF-8"))
                file.seek(0)

                update.effective_message.reply_document(
                    document=file,
                    filename="transactions.json",
                    caption=(
                        "You requested the export of your transaction log. "
                        f"This file contains all known transactions of {user.name}."
                    )
                )

        elif args.export == "csv":

            content = TransactionLog(user).to_csv(True)
            if content is None:
                update.effective_message.reply_text("You don't have any registered transactions yet.")
                return

            with tempfile.TemporaryFile(mode="w+b") as file:
                file.write(content.encode("UTF-8"))
                file.seek(0)

                update.effective_message.reply_document(
                    document=file,
                    filename="transactions.csv",
                    caption=(
                        "You requested the export of your transaction log. "
                        f"This file contains all known transactions of {user.name}."
                    )
                )

    @staticmethod
    def _handle_report(args: Namespace, update: telegram.Update) -> None:
        """
        Handle the request to report the most current transaction entries of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        user = MateBotUser(update.effective_message.from_user)
        logs = TransactionLog(user, args.length).to_list()
        log = "\n".join(logs)
        heading = f"Transaction history for {user.name}:\n```"
        if len(logs) == 0:
            update.effective_message.reply_text("You don't have any registered transactions yet.")
            return

        if update.effective_message.chat.type != update.effective_chat.PRIVATE:

            text = f"{heading}\n{log}```"
            if len(text) > 4096:
                update.effective_message.reply_text(
                    "Your requested transaction logs are too long. Try a smaller "
                    "number of entries or execute this command in private chat again."
                )
            else:
                update.effective_message.reply_markdown_v2(text)

        else:

            text = f"{heading}\n{log}```"
            if len(text) < 4096:
                update.effective_message.reply_markdown_v2(text)
                return

            results = [heading]
            for entry in logs:
                if len("\n".join(results + [entry])) > 4096:
                    results.append("```")
                    update.effective_message.reply_markdown_v2("\n".join(results))
                    results = ["```"]
                results.append(entry)

            if len(results) > 0:
                update.effective_message.reply_markdown_v2("\n".join(results + ["```"]))
