"""
MateBot inline query executors to forward collective operations
"""

import typing
import datetime

import telegram

from mate_bot.commands.base import BaseInlineQuery, BaseInlineResult
from mate_bot.commands.communism import Communism
from mate_bot.state.user import MateBotUser, CommunityUser
from mate_bot.state import finders


class CommunismInlineQuery(BaseInlineQuery):
    """
    User selection for forwarding communism messages to other users

    This feature is used to allow users to select a recipient from
    all known users in the database. This recipient will get the
    forwarded Communism message in a private chat message. To use
    this feature, the bot must be able to receive *all* updates
    for chosen inline query results. You may need to enable this
    updates via the @BotFather. Set the quota to 100%.
    """

    def get_result_id(
            self,
            communism_id: typing.Optional[int] = None,
            receiver: typing.Optional[int] = None
    ) -> str:
        """
        Generate a result ID based on the communism ID and receiving user

        Note that both a communism ID and a receiver are necessary in order
        to generate the result ID that encodes the information to forward a
        communism. If at least one of those parameters is not present, it's
        assumed that it's a help query. Note that the help query uses a
        different result ID format than the answers to the forwarding queries.

        :param communism_id: internal ID of the collective operation to be forwarded
        :type communism_id: typing.Optional[int]
        :param receiver: Telegram ID (Chat ID) of the recipient of the forwarded message
        :type receiver: typing.Optional[int]
        :return: string encoding information to forward communisms or a random UUID
        :rtype: str
        """

        now = int(datetime.datetime.now().timestamp())
        if communism_id is None or receiver is None:
            return f"communism-help-{now}"

        return f"communism-{now}-{communism_id}-{receiver}"

    def get_help(self) -> telegram.InlineQueryResultArticle:
        """
        Get the help option in the list of choices

        :return: inline query result choice for the help message
        :rtype: telegram.InlineQueryResultArticle
        """

        return self.get_result(
            "Help: What should I do here?",
            "*Help on using the inline mode of this bot*\n\n"
            "This bot enables users to forward communism and payment management "
            "messages to other users via a pretty comfortable inline search. "
            "Click on the button `FORWARD` of the message and then type the name, "
            "username or a part of it in the input field. There should already be "
            "a number besides the name of the bot. This number is required, forwarding "
            "does not work without this number. _Do not change it._ If you don't have "
            "a communism or payment message, you may try creating a new one. Use the "
            "commands /communism and /pay for this purpose, respectively. Use /help "
            "for a general help and an overview of other available commands."
        )

    def run(self, query: telegram.InlineQuery) -> None:
        """
        Search for a user in the database and allow the user to forward communisms

        :param query: inline query as part of an incoming Update
        :type query: telegram.InlineQuery
        :return: None
        """

        if len(query.query) == 0:
            return

        split = query.query.split(" ")

        try:
            comm_id = int(split[0])
            community = CommunityUser()

            users = []
            for word in split[1:]:
                if len(word) <= 1:
                    continue
                if word.startswith("@"):
                    word = word[1:]

                for target in finders.find_names_by_pattern(word):
                    user = finders.find_user_by_name(target)
                    if user is not None and user not in users:
                        if user.uid != community.uid:
                            users.append(user)

                for target in finders.find_usernames_by_pattern(word):
                    user = finders.find_user_by_username(target)
                    if user is not None and user not in users:
                        if user.uid != community.uid:
                            users.append(user)

            users.sort(key = lambda u: u.name.lower())

            answers = []
            for choice in users:
                answers.append(self.get_result(
                    str(choice),
                    f"I am forwarding this communism to {choice.name}...",
                    comm_id,
                    choice.tid
                ))

            query.answer([self.get_help()] + answers)

        except (IndexError, ValueError):
            query.answer([self.get_help()])


class CommunismInlineResult(BaseInlineResult):
    """
    Communism message forwarding based on the inline query result reports

    This feature is used to forward communism management messages
    to other users. The receiver of the forwarded message had to be
    selected by another user using the inline query functionality.
    The `result ID` should store the encoded timestamp, receiver
    Telegram ID and internal ID of the collective operation.
    """

    def run(self, result: telegram.ChosenInlineResult, bot: telegram.Bot) -> None:
        """
        Forward a communism management message to other users

        :param result: report of the chosen inline query option as part of an incoming Update
        :type result: telegram.ChosenInlineResult
        :param bot: currently used Telegram Bot object
        :type bot: telegram.Bot
        :return: None
        """

        # No exceptions will be handled because errors here would mean
        # problems with the result ID which is generated by the bot itself
        command_name, ts, comm_id, receiver = result.result_id.split("-")
        if command_name != "communism":
            return

        comm_id = int(comm_id)
        receiver = int(receiver)
        user = MateBotUser(MateBotUser.get_uid_from_tid(receiver))

        Communism((comm_id, user, bot))
