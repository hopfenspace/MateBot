"""
MateBot command executor classes for /zwegat
"""

import logging

from nio import MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.state import User
from mate_bot.commands.base import BaseCommand, INTERNAL
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class ZwegatCommand(BaseCommand):
    """
    Command executor for /zwegat
    """

    def __init__(self):
        super().__init__(
            "zwegat",
            "Use this command to show the central funds.\n\n"
            "This command can only be used by internal users.",
            "Use this command to show the central funds.<br /><br />"
            "This command can only be used by internal users."
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

        if not self.ensure_permissions(user, INTERNAL, api, event, room):
            return

        total = User.community_user().balance / 100
        if total >= 0:
            msg = f"Peter errechnet ein massives Vermögen von {total:.2f}€"
        else:
            msg = f"Peter errechnet Gesamtschulden von {-total:.2f}€"
        await api.send_reply(msg, room, event, send_as_notice=True)
