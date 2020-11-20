"""
MateBot command executor classes for /help
"""

import logging

from nio import RoomMessageText, MatrixRoom
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.state import User
from mate_bot import registry
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.types import command as command_type
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class HelpCommand(BaseCommand):
    """
    Command executor for /help
    """

    def __init__(self):
        super().__init__(
            "help",
            "The help command prints the help page for any "
            "command. If no argument is passed, it will print its "
            "usage and a list of all available commands.",
            "The <code>help</code> command prints the help page for any "
            "command. If no argument is passed, it will print its "
            "usage and a list of all available commands."
        )

        self.parser.add_argument("command", type=command_type, nargs="?")

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

        if args.command:
            usages = "\n".join(map(lambda x: f"{api.config.matrix.command_prefix} {args.command.name} {x}", args.command.parser.usages))
            usages_formatted = "<br />".join(map(lambda x: f"<code>{api.config.matrix.command_prefix} {args.command.name} {x}</code>", args.command.parser.usages))
            msg = f"Usages:\n{usages}\n\nDescription:\n{args.command.description}"
            msg_formatted = f"<em>Usages:</em><br />{usages_formatted}<br /><br /><em>Description:</em><br />{args.command.description_formatted}"

        else:
            command_list = "\n".join(map(lambda c: f" - {c}", sorted(registry.commands.keys())))
            msg = f"{self.usage}\n\nList of commands:\n\n{command_list}"
            msg_formatted = f"{self.usage}<br /><br /><em>List of commands:</em><br /><br />{command_list}"

            if user.external:
                msg += "\n\nYou are an external user. Some commands may be restricted."
                msg_formatted += "<br /><br />You are an external user. Some commands may be restricted."

                if user.creditor is None:
                    msg += (
                        f"\nYou don't have any creditor. Your possible interactions "
                        f"with the bot are very limited for security purposes. You "
                        f"can ask some internal user to act as your voucher. To "
                        f"do this, the internal user needs to execute {api.config.matrix.command_prefix} vouch "
                        f"<your username>. Afterwards, you may use this bot."
                    )
                    msg_formatted += (
                        f"<br />You don't have any creditor. Your possible interactions "
                        f"with the bot are very limited for security purposes. You "
                        f"can ask some internal user to act as your voucher. To "
                        f"do this, the internal user needs to execute <code>{api.config.matrix.command_prefix} vouch "
                        f"<your username></code>. Afterwards, you may use this bot."
                    )

        await api.send_reply(msg, room, event, formatted_message=msg_formatted, send_as_notice=True)
