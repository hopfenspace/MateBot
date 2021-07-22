"""
MateBot command executor classes for /start
"""

import logging

import telegram

from matebot_core.state.user import MateBotUser
from matebot_core.config import config
from matebot_core.commands.base import BaseCommand
from matebot_core.parsing.util import Namespace


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

    def run(self, args: Namespace, update: telegram.Update) -> None:
        """
        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        """

        if update.message is None:
            return

        sender = update.message.from_user
        if sender.is_bot:
            return

        external = update.message.chat.id != config["chats"]["internal"]
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
