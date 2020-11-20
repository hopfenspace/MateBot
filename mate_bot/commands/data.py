"""
MateBot command executor classes for /data
"""

import logging

from nio import MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.state import User
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class DataCommand(BaseCommand):
    """
    Command executor for /data
    """

    def __init__(self):
        super().__init__(
            "data",
            "Use this command to see the data the bot has stored about you.\n\n"
            "This command can only be used in private chat to protect private data.\n"
            "To view your transactions, use the command `/history` instead."
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

        if not api.is_room_private(room):
            msg = "This command can only be used in private chat."

        else:
            user = User.get(event.sender)

            if user.external:
                relations = f"Creditor user: {user.creditor}"

            else:
                users = ", ".join(map(str, user.debtors))
                if users == "":
                    users = "None"
                relations = f"Debtor user{'s' if len(users) != 1 else ''}: {users}"

            msg = (
                f"Overview over currently stored data for {user}:\n"
                f"\n\n"
                f"User ID: {user.id}\n"
                f"Matrix ID: {user.matrix_id}\n"
                f"Display Name: {user.display_name}\n"
                f"Balance: {user.balance / 100 :.2f}€\n"
                f"Vote permissions: {user.permission}\n"
                f"External user: {user.external}\n"
                f"{relations}\n"
                f"Account created: {user.created}\n"
                f"Last transaction: {user.accessed}\n"
                f"\n"
                f"Use the /history command to see your transaction log."
            )

        await api.send_message(msg, room.room_id, send_as_notice=True)
