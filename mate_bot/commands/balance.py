"""
MateBot command executor classes for /balance
"""

import logging

from nio import MatrixRoom, RoomMessageText, AsyncClient
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.statealchemy import User
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.types import user as user_type
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class BalanceCommand(BaseCommand):
    """
    Command executor for /balance
    """

    def __init__(self, api: ApiWrapper):
        super().__init__(
            api,
            "balance",
            "Use this command to show a user's balance.\n\n"
            "When you use this command without arguments, the bot will "
            "reply with your current amount of money stored in your virtual "
            "wallet. If you specify a username or mention someone as an argument,"
            "the 'balance' of this user is returned instead of yours."
        )

        self.parser.add_argument("user", type=user_type, nargs="?")

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

        if args.user:
            user = args.user
            msg = f"Balance of {user.name} is: {user.balance / 100 : .2f}€"

        else:
            user = User.get_or_create(event.sender)
            msg =f"Your balance is: {user.balance / 100 :.2f}€"

        await self.api.send_message(msg, room.room_id, send_as_notice=True)
