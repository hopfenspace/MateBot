"""
MateBot command executor classes for /help
"""

import typing
import logging
import datetime

from nio import AsyncClient, RoomMessageText, MatrixRoom

from mate_bot import registry
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.types import command as command_type
from mate_bot.parsing.util import Namespace
from mate_bot.state.user import MateBotUser


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
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if args.command:
            usages = "\n".join(map(lambda x: f"`/{args.command.name} {x}`", args.command.parser.usages))
            msg = f"*Usages:*\n{usages}\n\n*Description:*\n{args.command.description}"

        else:
            #user = MateBotUser(update.effective_message.from_user)
            #msg = self.get_help_usage(registry.commands, self.usage, user)
            msg = "NotImplemented"

        await self.client.room_send(
            room.room_id,
            "m.notice",
            {"msgtype": "m.notice", "body": msg},
            ignore_unverified_devices=True
        )
        #update.effective_message.reply_markdown(msg)

    @staticmethod
    def get_help_usage(
            commands: dict,
            usage: str,
            user: typing.Optional[MateBotUser] = None
    ) -> str:
        """
        Retrieve the help message from the help command without arguments

        :param commands: dictionary of registered commands, see :mod:`mate_bot.registry`
        :type commands: dict
        :param usage: usage string of the help command
        :type usage: str
        :param user: optional MateBotUser object who issued the help command
        :type user: typing.Optional[MateBotUser]
        :return: fully formatted help message when invoking the help command without arguments
        :rtype: str
        """

        command_list = "\n".join(map(lambda c: f" - `{c}`", sorted(commands.keys())))
        msg = f"{usage}\n\nList of commands:\n\n{command_list}"

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

        return msg
