"""
MateBot command executor classes for /history
"""

import json
import logging
import tempfile

from nio import MatrixRoom, RoomMessageText, UploadResponse
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.state import Transaction
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
            "as downloadable file. Currently supported formats are csv and json. "
            "Just add one of those two format specifiers after the command. Note "
            "that this variant is restricted to your personal chat with the bot.",
            "Use this command to get an overview of your transactions.<br /><br />"
            "You can specify the number of most recent transactions (default "
            "10) which will be returned by the bot. Using a huge number will "
            "just print all your transactions, maybe in multiple messages.<br /><br />"
            "You could also export the whole history of your personal transactions "
            "as downloadable file. Currently supported formats are <code>csv</code> and <code>json</code>. "
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

    async def run(self, args: Namespace, api: ApiWrapper, room: MatrixRoom, event: RoomMessageText) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param api: the api to respond with
        :type api: hopfenmatrix.api_wrapper.ApiWrapper
        :param room: room the message came in
        :type room: nio.MatrixRoom
        :param event: incoming message event
        :type event: nio.RoomMessageText
        :return: None
        """
        user = await self.get_sender(api, room, event)

        logs = Transaction.history(user, args.length)

        if len(logs) == 0:
            msg = "You don't have any registered transactions yet."
            await api.send_reply(msg, room, event, send_as_notice=True)

        elif args.export is None:
            if not await api.is_room_private(room) and len(logs) > 20:
                msg = ("Your requested transaction logs are too long. Try a smaller "
                       "number of entries or execute this command in private chat again.")
                await api.send_reply(msg, room, event, send_as_notice=True)

            else:
                msg = f"Transaction history for {user}:\n\n" + "\n".join(map(str, logs))
                formatted_msg = (f"Transaction history for {user}:<br /><br />"
                                 f"<pre><code>{'<br />'.join(map(str, logs))}</code></pre>")
                await api.send_reply(msg, room, event, formatted_message=formatted_msg, send_as_notice=True)

        else:
            if not await api.is_room_private(room):
                await api.send_reply("This command can only be used in private chat.", room, event, send_as_notice=True)

            else:
                logs = list(map(Transaction.as_exportable_dict, logs))

                if args.export == "json":
                    text = json.dumps(logs, indent=2)

                else:  # args.export == "csv":
                    text = ";".join(logs[0].keys())
                    for log in logs:
                        text += "\n" + ";".join(map(str, log.values()))

                with tempfile.NamedTemporaryFile(mode="w+b") as file:
                    file.write(text.encode("utf-8"))
                    file.seek(0)

                    await api.send_file(file.name, room, description=f"transaction.{args.export}")
