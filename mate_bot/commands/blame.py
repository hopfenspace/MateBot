"""
MateBot command executor classes for /blame
"""

import logging

from nio import MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.commands.base import BaseCommand, INTERNAL
from mate_bot.parsing.util import Namespace
from mate_bot.state import User


logger = logging.getLogger("commands")


class BlameCommand(BaseCommand):
    """
    Command executor for blame
    """

    def __init__(self):
        super().__init__(
            "blame",
            "Use this command to show the user(s) with the highest debts.\n\n"
            "Put the user(s) with the highest debts to the pillory and make them "
            "settle their debts, e.g. by buying stuff like new bottle crates. "
            "This command can only be executed by internal users.",
            "Use this command to show the user(s) with the highest debts.\n\n"
            "Put the user(s) with the highest debts to the pillory and make them "
            "settle their debts, e.g. by buying stuff like new bottle crates. "
            "This command can only be executed by internal users."
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

        if not await self.ensure_permissions(user, INTERNAL, api, event, room):
            return

        debtors = User.put_blame()

        if len(debtors) == 1:
            msg = "The user with the highest debt is:\n"
        else:
            msg = "The users with the highest debts are:\n"
        msg += "\n".join(map(str, debtors))

        await api.send_reply(msg, room, event, send_as_notice=True)
