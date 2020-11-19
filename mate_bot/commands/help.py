"""
MateBot command executor classes for /help
"""

import logging

from nio import AsyncClient, RoomMessageText, MatrixRoom

from mate_bot import registry
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.types import command as command_type
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class HelpCommand(BaseCommand):
    """
    Command executor for /help
    """

    def __init__(self, client: AsyncClient):
        super().__init__(
            client,
            "help",
            "The `/help` command prints the help page for any "
            "command. If no argument is passed, it will print its "
            "usage and a list of all available commands."
        )

        self.parser.add_argument("command", type=command_type, nargs="?")

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

        if args.command:
            usages = "\n".join(map(lambda x: f"`/{args.command.name} {x}`", args.command.parser.usages))
            msg = f"*Usages:*\n{usages}\n\n*Description:*\n{args.command.description}"

        else:
            command_list = "\n".join(map(lambda c: f" - `{c}`", sorted(registry.commands.keys())))
            msg = f"{self.usage}\n\nList of commands:\n\n{command_list}"

            '''
            user = MateBotUser(event.sender)
            if user and isinstance(user, MateBotUser) and user.external:
                msg += "\n\nYou are an external user. Some commands may be restricted."

                if user.creditor is None:
                    msg += (
                        "\nYou don't have any creditor. Your possible interactions "
                        "with the bot are very limited for security purposes. You "
                        "can ask some internal user to act as your voucher. To "
                        "do this, the internal user needs to execute `/vouch "
                        "<your username>`. Afterwards, you may use this bot."
                    )
            '''

        await self.client.room_send(
            room.room_id,
            "m.room.message",
            {"msgtype": "m.notice", "format": "plain", "body": msg},
            ignore_unverified_devices=True
        )
