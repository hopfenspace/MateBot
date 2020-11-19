"""
MateBot command executor classes for /data
"""

import logging

from nio import MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.statealchemy import User
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class DataCommand(BaseCommand):
    """
    Command executor for /data
    """

    def __init__(self, api: ApiWrapper):
        super().__init__(
            api,
            "data",
            "Use this command to see the data the bot has stored about you.\n\n"
            "This command can only be used in private chat to protect private data.\n"
            "To view your transactions, use the command `/history` instead."
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

        #if update.effective_message.chat.type != "private":
        #    update.effective_message.reply_text("This command can only be used in private chat.")
        #    return

        user = User.get(event.sender)

        '''
        if user.external:
            if user.creditor:
                creditor = MateBotUser(user.creditor)
                relations = f"Creditor user: {creditor.name}"
                if creditor.username:
                    relations += f" ({creditor.username})"
            else:
                relations = "Creditor user: None"

        else:
            users = ", ".join(map(
                lambda u: f"{u.name} ({u.username})" if u.username else u.name,
                map(
                    lambda i: MateBotUser(i),
                    user.debtors
                )
            ))
            if len(users) == 0:
                users = "None"
            relations = f"Debtor user{'s' if len(users) != 1 else ''}: {users}"
        '''

        result = (
            f"Overview over currently stored data for {user.name}:\n"
            f"\n```\n"
            f"User ID: {user.id}\n"
            f"Matrix ID: {user.matrix_id}\n"
            f"Name: {user.name}\n"
            f"Username: {user.username}\n"
            f"Balance: {user.balance / 100 :.2f}€\n"
            f"Vote permissions: {user.permission}\n"
            f"External user: {user.external}\n"
            # f"{relations}\n"
            f"Account created: {user.created}\n"
            f"Last transaction: {user.accessed}\n"
            f"```\n"
            f"Use the /history command to see your transaction log."
        )

        await self.api.send_message(result, room.room_id, send_as_notice=True)
