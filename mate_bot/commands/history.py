"""
MateBot command executor classes for /history
"""

import csv
import json
import logging
import tempfile

from nio import MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.statealchemy import User, Transaction
from mate_bot.parsing.types import natural as natural_type
from mate_bot.parsing.util import Namespace
from mate_bot.commands.base import BaseCommand


logger = logging.getLogger("commands")


class HistoryCommand(BaseCommand):
    """
    Command executor for /history
    """

    def __init__(self, api: ApiWrapper):
        super().__init__(
            api,
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

    async def run(self, args: Namespace, room: MatrixRoom, event: RoomMessageText) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param room: room the message came in
        :type room: nio.MatrixRoom
        :param event: incoming message event
        :type event: nio.RoomMessageText
        :return: None
        """

        if args.export is None:
            await self._handle_report(args, room, event)
        else:
            await self._handle_export(args, room, event)

    async def _handle_export(self, args: Namespace, room: MatrixRoom, event: RoomMessageText) -> None:
        """
        Handle the request to export the full transaction log of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param room: room to reply in
        :type room: nio.MatrixRoom
        :return: None
        """

        '''
        if update.effective_chat.type != update.effective_chat.PRIVATE:
            update.effective_message.reply_text("This command can only be used in private chat.")
            return

        user = MateBotUser(update.effective_message.from_user)
        logs = TransactionLog(user).to_json()
        if len(logs) == 0:
            update.effective_message.reply_text("You don't have any registered transactions yet.")
            return

        if args.export == "json":

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

            with tempfile.TemporaryFile(mode="w+") as file:
                writer = csv.DictWriter(file, fieldnames=logs[0].keys(), quoting=csv.QUOTE_ALL)
                writer.writeheader()
                writer.writerows(logs)
                file.seek(0)
                content = file.read().encode("UTF-8")

            with tempfile.TemporaryFile(mode="w+b") as file:
                file.write(content)
                file.seek(0)
                update.effective_message.reply_document(
                    document=file,
                    filename="transactions.csv",
                    caption=(
                        "You requested the export of your transaction log. "
                        f"This file contains all known transactions of {user.name}."
                    )
                )
        '''
        await self.api.send_message("NotImplementedError", room.room_id, send_as_notice=True)

    async def _handle_report(self, args: Namespace, room: MatrixRoom, event: RoomMessageText) -> None:
        """
        Handle the request to report the most current transaction entries of a user

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param room: room to reply in
        :type room: nio.MatrixRoom
        :return: None
        """

        user = User(event.sender)
        logs = Transaction.get(user, args.length)

        heading = f"Transaction history for {user.name}:\n\n"
        text = heading + "\n".join(map(str, logs))

        if len(logs) == 0:
            await self.api.send_message("You don't have any registered transactions yet.", room.room_id, send_as_notice=True)
            return

        #elif update.effective_message.chat.type != update.effective_chat.PRIVATE:
        #    if len(text) > 4096:
        #        update.effective_message.reply_text(
        #            "Your requested transaction logs are too long. Try a smaller "
        #            "number of entries or execute this command in private chat again."
        #        )
        #    else:
        #        update.effective_message.reply_markdown_v2(text)

        else:
            if len(text) < 4096:
                await self.api.send_message(text, room.room_id, send_as_notice=True)
                return

            else:
                results = heading
                for entry in map(str, logs):
                    if len(f"{results}\n{entry}") > 4096:
                        await self.api.send_message(results, room.room_id, send_as_notice=True)
                        results = ""
                    results += "\n" + entry

                await self.api.send_message(results, room.room_id, send_as_notice=True)
