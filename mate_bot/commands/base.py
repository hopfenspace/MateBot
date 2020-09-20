"""
MateBot command handling base library
"""

import typing
import argparse

import telegram.ext

from mate_bot import state
from mate_bot.err import ParsingError
from mate_bot.args.parser import PatchedParser
from mate_bot.args.pre_parser import pre_parse
from mate_bot.args.formatter import format_usage


class BaseCommand:
    """
    Base class for all MateBot commands executed by the CommandHandler

    It handles argument parsing and exception catching. Some specific
    implementation should be a subclass of this class. It must add
    arguments to the parser in the constructor and overwrite the run method.

    A minimal working example class may look like this:

        class ExampleCommand(BaseCommand):
            def __init__(self):
                super().__init__("example")
                self.parser.add_argument("number", type=int)

            def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
                update.effective_message.reply_text(
                    " ".join(["Example!"] * max(1, args.number))
                )

    :param name: name of the command (without the "/")
    :type name: str
    :param description: a multiline string describing what the command does
    :type description: str
    :param usage: a single line string showing the basic syntax
    :type usage: Optional[str]
    """

    # Dict to look up a commands class via its name
    COMMAND_DICT = {}

    def __init__(self, name: str, description: str, usage: typing.Optional[str] = None):

        # Put the command in the command dict
        if name not in BaseCommand.COMMAND_DICT:
            BaseCommand.COMMAND_DICT[name] = type(self)

        self.name = name
        self._usage = usage
        self.description = description
        self.parser = PatchedParser(name)

    @property
    def usage(self):
        if self._usage is None:
            return format_usage(self.parser)
        else:
            return self._usage

    def run(self, args: argparse.Namespace, update: telegram.Update) -> None:
        """
        Perform command-specific actions

        This method should be overwritten in actual commands to perform the desired action.

        :param args: parsed namespace containing the arguments
        :type args: argparse.Namespace
        :param update: incoming Telegram update
        :type update: telegram.Update
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseCommand.run() method in a subclass")

    def __call__(self, update: telegram.Update, context: telegram.ext.CallbackContext) -> None:
        """
        Parse arguments of the incoming update and execute the .run() method

        This method is the callback method used by telegram.CommandHandler.
        Note that this method also catches any exceptions and prints them.

        :param update: incoming Telegram update
        :type update: telegram.Update
        :param context: Telegram callback context
        :type context: telegram.ext.CallbackContext
        :return: None
        """

        try:
            if self.name != "start":
                if state.MateBotUser.get_uid_from_tid(update.effective_message.from_user.id) is None:
                    update.effective_message.reply_text("You need to /start first.")
                    return
            argv = pre_parse(update.effective_message)
            args = self.parser.parse_args(argv)
            self.run(args, update)

        except ParsingError as err:
            update.effective_message.reply_text(
                str(err) + "\n" + self.usage
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
    """

    def __init__(
            self,
            name: str,
            targets: typing.Optional[typing.Dict[str, typing.Callable]] = None
    ):
        """
        :param name: name of the command the callback is for
        :type name: str
        :param targets: dict to associate data replies with function calls
        :type targets: typing.Optional[typing.Dict[str, typing.Callable]]
        """

        if not isinstance(targets, dict) and targets is not None:
            raise TypeError("Expected dict or None")

        self.name = name
        self.data = None
        self.targets = targets

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

    :param origin: feature that forced the user to perform the inline query (if available)
    :type origin: typing.Callable
    """

    def __init__(self, origin: typing.Optional[typing.Callable] = None):
        self.origin = origin

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

        self.run(update.inline_query)

    def get_help(self) -> telegram.InlineQueryResult:
        """
        Get some kind of help message as inline result (always as first item!)

        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.run() method in a subclass")

    def run(self, query: telegram.InlineQuery) -> None:
        """
        Perform command-specific operations

        :param query: incoming Telegram update
        :type query: telegram.Update
        :return: None
        :raises NotImplementedError: because this method should be overwritten by subclasses
        """

        raise NotImplementedError("Overwrite the BaseInlineQuery.run() method in a subclass")


class BaseInlineResult:
    """
    Base class for all MateBot inline query results executed by the ChosenInlineResultHandler
    """
