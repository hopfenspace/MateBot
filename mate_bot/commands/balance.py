"""
MateBot command executor classes for /balance
"""

import logging

from nio import MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.state import User
from mate_bot.commands.base import BaseCommand, INTERNAL
from mate_bot.parsing.types import user as user_type
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class BalanceCommand(BaseCommand):
    """
    Command executor for /balance
    """

    def __init__(self):
        super().__init__(
            "balance",
            "Use this command to show a user's balance.\n\n"
            "When you use this command without arguments, the bot will "
            "reply with your current amount of money stored in your virtual "
            "wallet. If you specify a username or mention someone as an argument,"
            "the 'balance' of this user is returned instead of yours.",
            "Use this command to show a user's balance.\n\n"
            "When you use this command without arguments, the bot will "
            "reply with your current amount of money stored in your virtual "
            "wallet. If you specify a username or mention someone as an argument,"
            "the 'balance' of this user is returned instead of yours."
        )

        self.parser.add_argument("user", type=user_type, nargs="?")

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
        sender = await self.get_sender(api, room, event)

        if args.user:
            if not await self.ensure_permissions(sender, INTERNAL, api, event, room):
                return

            msg = f"Balance of {args.user} is: {args.user.balance / 100 : .2f}€"

        else:
            msg = f"Your balance is: {sender.balance / 100 :.2f}€"

        await api.send_reply(msg, room, event, send_as_notice=True)
