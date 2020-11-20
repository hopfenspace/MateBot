"""
MateBot command executor classes for /start
"""

import logging

from nio import AsyncClient, MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.statealchemy import User
from mate_bot.commands.base import BaseCommand
from mate_bot.parsing.util import Namespace


logger = logging.getLogger("commands")


class StartCommand(BaseCommand):
    """
    Command executor for /start
    """

    def __init__(self):
        super().__init__(
            "start",
            "Use this command once per user to start interacting with this bot.\n\n"
            "This command creates your user account in case it was not yet. Otherwise, "
            "this command might not be pretty useful. Note that you should not delete "
            "the chat with the bot in order to receive personal notifications from it.\n\n"
            "Use /help for more information about how to use this bot and its commands."
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

        try:
            user = User.get(event.sender)
            msg = f"You are already registered, {event.sender}"
        except ValueError:
            user = User.new(event.sender)
            msg = f"Thank you for registering, {event.sender}"

        await api.send_message(msg, room.room_id, send_as_notice=True)
        '''
        external = update.message.chat.id != config["bot"]["chat"]
        if external and update.message.chat.type != "private":
            update.message.reply_text("This command should be executed in private chat.")
            return

        if MateBotUser.get_uid_from_tid(sender.id) is not None:
            user = MateBotUser(sender)
            if not external and user.external:
                user.external = external
                update.message.reply_text(
                    "Your account was updated. You are now an internal user."
                )
            return

        user = MateBotUser(sender)
        user.external = external

        answer = (
            "**Your user account was created.** You are currently marked as "
            f"{'external' if external else 'internal'} user without vote permissions."
        )

        if external:
            answer += (
                "\n\nIn order to be marked as internal user, you have to "
                "send the `/start` command to a privileged chat once. If "
                "you don't have access to them, you may ask someone to invite "
                "you.\nAlternatively, you can ask some internal user to act as your "
                "voucher. To do this, the internal user needs to execute `/vouch "
                "<your username>`. Afterwards, you may use this bot."
            )

        update.message.reply_markdown(answer)
        '''
