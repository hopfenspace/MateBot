import argparse

import telegram

from mate_bot import state
from mate_bot.config import config
from mate_bot.commands.base import BaseCommand


class StartCommand(BaseCommand):
    """
    Command executor for /start
    """

    def __init__(self):
        super().__init__("start", "")
        self.parser.add_argument("trash-bin", nargs="*")

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
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

        external = True
        if update.message.chat.id == config["bot"]["chat"]:
            external = False

        elif update.message.chat.type != "private":
            update.message.reply_text("This command should be executed in private chat.")
            return

        if state.MateBotUser.get_uid_from_tid(sender.id) is not None:
            user = state.MateBotUser(sender)
            if not external and user.external:
                user.external = external
                update.message.reply_text(
                    "Your account was updated. You are now an internal user."
                )
            return

        user = state.MateBotUser(sender)
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
