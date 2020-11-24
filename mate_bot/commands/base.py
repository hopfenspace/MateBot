"""
MateBot command handling base library
"""

import typing
import logging

from nio import MatrixRoom, RoomMessageText
from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.state import User
from mate_bot import registry
from mate_bot.err import ParsingError
from mate_bot.parsing.parser import CommandParser
from mate_bot.parsing.util import Namespace
from mate_bot.config import config


logger = logging.getLogger("commands")


ANYONE = 0
VOUCHED = 1
INTERNAL = 2
TRUSTED = 3


class BaseCommand:
    """
    Base class for all MateBot commands executed by the CommandHandler

    It handles argument parsing and exception catching. Some specific
    implementation should be a subclass of this class. It must add
    arguments to the parser in the constructor and overwrite the run method.

    A minimal working example class may look like this:

    .. code-block::

        class ExampleCommand(BaseCommand):
            def __init__(self):
                super().__init__("example", "Example command")
                self.parser.add_argument("number", type=int)

            def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
                update.effective_message.reply_text(
                    " ".join(["Example!"] * max(1, args.number))
                )

    :param name: name of the command (without the "/")
    :type name: str
    :param description: a multiline string describing what the command does
    :type description: str
    :param description_formatted: a multiline string describing what the command does. Formatted with html.
    :type description_formatted: str
    :param usage: a single line string showing the basic syntax
    :type usage: Optional[str]
    """

    def __init__(self, name: str, description: str, description_formatted:str, usage: typing.Optional[str] = None):
        self.name = name
        self._usage = usage
        self.description = description
        self.description_formatted = description_formatted
        self.parser = CommandParser(self.name)

        registry.commands[self.name] = self

    @property
    def usage(self) -> str:
        """
        Get the usage string of a command
        """

        if self._usage is None:
            return f"!{self.name} {self.parser.default_usage}"
        else:
            return self._usage

    async def run(self, args: Namespace, api: ApiWrapper, room: MatrixRoom, event: RoomMessageText) -> None:
        """
        Perform command-specific actions

        This method should be overwritten in actual commands to perform the desired action.

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param api: the api to respond with
        :type api: hopfenmatrix.api_wrapper.ApiWrapper
        :param room: room the message came in
        :type room: nio.MatrixRoom
        :param event: incoming message event
        :type event: nio.RoomMessageText
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseCommand.run() method in a subclass")

    async def __call__(self, api: ApiWrapper, room: MatrixRoom, event: RoomMessageText) -> None:
        """
        Parse arguments of the incoming event and execute the .run() method

        This method is the callback method used by `AsyncClient.add_callback_handler`.

        :param api: the api to respond with
        :type api: hopfenmatrix.api_wrapper.ApiWrapper
        :param room: room the message came in
        :type room: nio.MatrixRoom
        :param event: incoming message event
        :type event: nio.RoomMessageText
        :return: None
        """
        try:
            logger.debug(f"{type(self).__name__} by {event.sender}")

            """if self.name != "start":
                if MateBotUser.get_uid_from_tid(event.sender) is None:
                    #update.effective_message.reply_text("You need to /start first.")
                    return

                #user = MateBotUser(event.sender)
                #self._verify_internal_membership(update, user, context.bot)"""

            args = self.parser.parse(event)
            logger.debug(f"Parsed command's arguments: {args}")
            await self.run(args, api, room, event)

        except ParsingError as err:
            await api.send_message(str(err), room, event, send_as_notice=True)

    @staticmethod
    async def get_sender(api: ApiWrapper, room: MatrixRoom, event: RoomMessageText) -> User:
        try:
            user = User.get(event.sender)
        except ValueError:
            user = User.new(event.sender)
            await api.send_reply(f"Welcome {user}, please enjoy your drinks", room, event, send_as_notice=True)

            if room.room_id != config.room:
                user.external = True

        display_name = (await api.client.get_displayname(user.matrix_id)).displayname
        if display_name != user.display_name:
            user.display_name = display_name
            user.push()

        if room.room_id == config.room and user.external:
            user.external = False
            await api.send_reply(f"{user}, you are now an internal.", room, event, send_as_notice=True)

        return user

    async def ensure_permissions(
            self,
            user: User,
            level: int,
            api: ApiWrapper,
            event: RoomMessageText,
            room: MatrixRoom
    ) -> bool:
        """
        Ensure that a user is allowed to perform an operation that requires specific permissions

        The parameter ``level`` is a constant and determines the required
        permission level. It's not calculated but rather interpreted:

          * ``ANYONE`` means that any user is allowed to perform the task
          * ``VOUCHED`` means that any internal user or external user with voucher is allowed
          * ``INTERNAL`` means that only internal users are allowed
          * ``TRUSTED`` means that only internal users with vote permissions are allowed

        .. note::

            This method will automatically reply to the incoming message when
            the necessary permissions are not fulfilled. Use the return value
            to determine whether you should simply quit further execution of
            your method (returned ``False``) or not (returned ``True``).

        :param user: MateBotUser that tries to execute a specific command
        :type user: MateBotUser
        :param level: minimal required permission level to be allowed to perform some action
        :type level: int
        :param api: api to reply with
        :type api: hopfenmatrix.api_wrapper.ApiWrapper
        :param event: event to reply to
        :type event: nio.RoomMessageText
        :param room: room to reply in
        :type room: nio.MatrixRoom
        :return: whether further access should be allowed (``True``) or not
        :rtype: bool
        """
        if level == VOUCHED and user.external and user.creditor is None:
            msg = (
                f"You can't perform {self.name}. You are an external user "
                "without creditor. For security purposes, every external user "
                "needs an internal voucher. Use /help for more information."
            )

        elif level == INTERNAL and user.external:
            msg = (
                f"You can't perform {self.name}. You are an external user. "
                "To perform this command, you must be marked as internal user. "
                "Send any command to an internal chat to update your privileges."
            )

        elif level == TRUSTED and not user.permission:
            msg = (
                f"You can't perform {self.name}. You don't have permissions to vote."
            )

        else:
            return True

        await api.send_reply(msg, room, event, send_as_notice=True)
        return False


'''
    def _verify_internal_membership(
            self,
            update: telegram.Update,
            user: "MateBotUser",
            bot: telegram.Bot
    ) -> None:
        """
        Verify that a user who calls a command from the internal chat is marked as internal user

        :param update: incoming Telegram update
        :type update: telegram.Update
        :param user: existing MateBotUser that executed a command (not ``/start``)
        :type user: MateBotUser
        :param bot: Telegram Bot object that can send messages to clients
        :type bot: telegram.Bot
        :return: None
        """

        external = update.effective_message.chat.id != config["chats"]["internal"]
        if external or not user.external:
            return

        creditor = user.creditor
        if creditor is None:
            user.external = external
            bot.send_message(
                user.tid,
                "Your account was updated. You are now an internal "
                f"user because you executed /{self.name} in an internal chat."
            )
        else:
            bot.send_message(
                user.tid,
                f"You receive this message because you executed /{self.name} in "
                "an internal chat. It looks like {MateBotUser(creditor)} vouches "
                f"for you. You can't have a voucher when you try to become an internal "
                f"user. Therefore, your account status was not updated."
            )


class BaseCallbackQuery:
    """
    Base class for all MateBot callback queries executed by the CallbackQueryHandler

    It provides the stripped data of a callback button as string
    in the data attribute. Some specific implementation should be
    a subclass of this class. It must either overwrite the run method
    or provide the constructor's parameter `targets` to work properly.
    The `targets` parameter is a dictionary connecting the data with
    associated function calls. Those functions or methods must
    expect one parameter `update` which is filled with the correct
    telegram.Update object. No return value is expected.

    In order to properly use this class or a subclass thereof, you
    must supply a pattern to filter the callback query against to
    the CallbackQueryHandler. This pattern must start with `^` to
    ensure that it's the start of the callback query data string.
    Furthermore, this pattern must match the name you give as
    first argument to the constructor of this class.

    Example: Imagine you have a command `/hello`. The callback query
    data should by convention start with "hello". So, you set
    "hello" as the name of this handler. Furthermore, you set
    "^hello" as pattern to filter callback queries against.

    :param name: name of the command the callback is for
    :type name: str
    :param pattern: regular expression to filter callback query executors
    :type pattern: str
    :param targets: dict to associate data replies with function calls
    :type targets: Optional[typing.Dict[str, typing.Callable]]
    """

    def __init__(
            self,
            name: str,
            pattern: str,
            targets: typing.Optional[typing.Dict[str, typing.Callable]] = None
    ):

        if not isinstance(targets, dict) and targets is not None:
            raise TypeError("Expected dict or None")

        self.name = name
        self.pattern = pattern
        self.data = None
        self.targets = targets

        registry.callback_queries[self.pattern] = self

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        :raises RuntimeError: when either no callback data or no pattern match is present
        :raises IndexError: when a callback data string has no unique target callable
        :raises TypeError: when a target is not a callable object (implicitly)
        """

        data = update.callback_query.data
        logger.debug(f"{type(self).__name__} by {update.callback_query.from_user.name} with '{data}'")

        if data is None:
            raise RuntimeError("No callback data found")
        if context.match is None:
            raise RuntimeError("No pattern match found")

        self.data = (data[:context.match.start()] + data[context.match.end():]).strip()

        if self.targets is None:
            self.run(update)
            return

        if self.data in self.targets:
            self.targets[self.data](update)
            return

        available = []
        for k in self.targets:
            if self.data.startswith(k):
                available.append(k)

        if len(available) == 0:
            raise IndexError(f"No target callable found for: '{self.data}'")

        if len(available) > 1:
            raise IndexError(f"No unambiguous callable found for: '{self.data}'")

        self.targets[available[0]](update)

    def run(self, update: telegram.Update) -> None:
        """
        Perform command-specific operations

        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseCallbackQuery.run() method in a subclass")


class BaseInlineQuery:
    """
    Base class for all MateBot inline queries executed by the InlineQueryHandler

    :param pattern: regular expression to filter inline query executors
    :type pattern: str
    """

    def __init__(self, pattern: str):
        self.pattern = pattern

        registry.inline_queries[self.pattern] = self

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        :raises TypeError: when no inline query is attached to the Update object
        """

        if not hasattr(update, "inline_query"):
            raise TypeError('Update object has no attribute "inline_query"')

        query = update.inline_query
        logger.debug(f"{type(self).__name__} by {query.from_user.name} with '{query.query}'")
        self.run(query)

    def get_result_id(self, *args) -> str:
        """
        Get the ID of the inline result based on the given arguments

        :param args: any form of arguments that might be useful to create the result ID
        :type args: typing.Any
        :return: unique ID of the returned inline result so that the ChosenInlineResult
            can be parsed and used accurately (note that it doesn't need to be really unique)
        :rtype: str
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.get_result_id() method in a subclass")

    def get_result(
            self,
            heading: str,
            msg_text: str,
            *args,
            parse_mode: str = telegram.ParseMode.MARKDOWN
    ) -> telegram.InlineQueryResultArticle:
        """
        Get an article as possible inline result for an inline query

        :param heading: bold text (head line) the user clicks/taps on to select the inline result
        :type heading: str
        :param msg_text: text that will be sent from the client via the bot
        :type msg_text: str
        :param args: arguments passed to :meth:`get_result_id`
        :type args: typing.Any
        :param parse_mode: parse mode that should be used to parse this text (default: Markdown v1)
        :type parse_mode: str
        :return: inline query result (of type article)
        :rtype: telegram.InlineQueryResultArticle
        """

        return telegram.InlineQueryResultArticle(
            id=self.get_result_id(*args),
            title=heading,
            input_message_content=telegram.InputTextMessageContent(
                message_text=msg_text,
                parse_mode=parse_mode,
                disable_web_page_preview=True
            )
        )

    def get_help(self) -> telegram.InlineQueryResult:
        """
        Get some kind of help message as inline result (always as first item!)

        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.get_help() method in a subclass")

    def run(self, query: telegram.InlineQuery) -> None:
        """
        Perform feature-specific operations

        :param query: inline query as part of an incoming Update
        :type query: telegram.Update
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.run() method in a subclass")


class BaseInlineResult:
    """
    Base class for all MateBot inline query results executed by the ChosenInlineResultHandler

    :param pattern: regular expression to filter inline result executors
    :type pattern: str
    """

    def __init__(self, pattern: str):
        self.pattern = pattern

        registry.inline_results[self.pattern] = self

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        :raises TypeError: when no inline result is attached to the Update object
        """

        if not hasattr(update, "chosen_inline_result"):
            raise TypeError('Update object has no attribute "chosen_inline_result"')

        result = update.chosen_inline_result
        logger.debug(f"{type(self).__name__} by {result.from_user.name} with '{result.result_id}'")
        self.run(result, context.bot)

    def run(self, result: telegram.ChosenInlineResult, bot: telegram.Bot) -> None:
        """
        Perform feature-specific operations

        :param result: report of the chosen inline query option as part of an incoming Update
        :type result: telegram.ChosenInlineResult
        :param bot: currently used Telegram Bot object
        :type bot: telegram.Bot
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.run() method in a subclass")
'''
