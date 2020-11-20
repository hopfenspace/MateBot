"""
MateBot's CommandParser
"""

import typing

from nio import RoomMessageText

from mate_bot.err import ParsingError
from mate_bot.parsing.util import EntityString, Namespace, Representable
from mate_bot.parsing.usage import CommandUsage
from mate_bot.parsing.actions import Action
from mate_bot.parsing.formatting import plural_s


class CommandParser(Representable):
    """
    Class for parsing telegram messages into python objects.

    :param name: the command name the parser is for.
        This is used in error messages.
    :type name: str
    """

    def __init__(self, name: str):
        # Add initial default usage
        self._name = name
        self._usages = [CommandUsage()]

    @property
    def usages(self) -> typing.List[CommandUsage]:
        """
        Return list of usage objects
        """

        return self._usages

    @property
    def default_usage(self) -> CommandUsage:
        """
        Return the default usage added in constructor
        """

        return self._usages[0]

    def add_argument(self, *args, **kwargs) -> Action:
        """
        Add an argument to the default usage

        See `CommandUsage.add_argument` for type signature
        """

        return self._usages[0].add_argument(*args, **kwargs)

    def new_usage(self) -> CommandUsage:
        """
        Initialize, add and return a new usage object
        """

        self._usages.append(CommandUsage())
        return self._usages[-1]

    def parse(self, msg: RoomMessageText) -> Namespace:
        """
        Parse a telegram message into a namespace.

        This just combines the _split and _parse function.

        :param msg: message to parse
        :type msg: telegram.Message
        :return: parsed arguments
        :rtype: Namespace
        """

        # Split message into argument strings
        arg_strings = list(self._split(msg))

        # Remove bot command
        arg_strings = arg_strings[1:]

        # Parse
        return self._parse(arg_strings)

    def _parse(self, arg_strings: typing.List[str]) -> Namespace:
        """
        Internal function for parsing from a list of strings.

        :param arg_strings: a list of strings to parse
        :type arg_strings: List[str]
        :return: parsed arguments
        :rtype: Namespace
        """

        errors = []
        for usage in self._usages:
            if usage.min_arguments > len(arg_strings):
                errors.append(ParsingError(
                    f"requires at least {usage.min_arguments} argument{plural_s(usage.min_arguments)}."
                ))
                continue
            elif usage.max_arguments < len(arg_strings):
                errors.append(ParsingError(
                    f"allows at most {usage.max_arguments} argument{plural_s(usage.max_arguments)}."
                ))
                continue
            else:
                # Try the remaining ones
                try:
                    return self._parse_usage(usage, arg_strings)
                except ParsingError as err:
                    errors.append(err)
                continue

        # If you enter here, then all usages broke
        # Combine their error messages into one
        else:
            if len(self._usages):
                msg = ""
            else:
                msg = "No usage applies:"

            for usage, error in zip(self._usages, errors):
                msg += f"\n`/{self._name} {usage}` {error}"
            raise ParsingError(msg)

    def _parse_usage(self, usage: CommandUsage, arg_strings: typing.List[str]) -> Namespace:
        """
        Try to parse the arguments with a usage

        :param usage: the usage to parse the arguments with
        :type usage: CommandUsage
        :param arg_strings: argument strings to parse
        :type arg_strings: List[str]
        :return: parsed arguments
        :rtype: Namespace
        """

        # Shortcut out if there are no actions
        if len(usage.actions) == 0:
            return Namespace()

        # Initialize namespace and populate it with the defaults
        namespace = Namespace()
        for action in usage.actions:
            setattr(namespace, action.dest, action.default)

        def consume_action(local_action: Action, strings: typing.List[str]):
            """
            Use an action to consume as many argument strings as possible
            """

            values = []
            error = None

            while len(strings) > 0:
                string = strings.pop(0)

                try:
                    # Try converting the argument string
                    value = local_action.type(string)

                    # Check choices
                    if action.choices is not None and value not in action.choices:
                        raise ValueError(f"{value} is not an available choice, choose from "
                                         + ", ".join(map(lambda x: f"`{x}`", action.choices)))

                    # Add converted to list
                    values.append(value)

                    # Action can take more -> next string
                    if len(values) < local_action.max_args:
                        continue
                    else:
                        break

                except ValueError as err:
                    # Save error for later
                    error = err

                    # Put back unprocessed string
                    strings.insert(0, string)

                    break

            # Action isn't satisfied -> error
            if local_action.min_args > len(values):
                if error is not None:
                    raise ParsingError(str(error))
                else:
                    raise ParsingError(f"Missing argument{plural_s(local_action.min_args-len(values))}")

            # Action is satisfied -> finish with action
            else:
                # Process action
                if action.nargs is None:
                    local_action(namespace, values[0])
                elif action.nargs == "?":
                    if len(values) > 0:
                        local_action(namespace, values[0])
                else:
                    local_action(namespace, values)

        # Copy arg_strings to have a local list to mutate
        left_strings = list(arg_strings)

        for action in usage.actions:
            consume_action(action, left_strings)

        if len(left_strings) > 0:
            raise ParsingError(f"Unrecognized argument{plural_s(left_strings)}: {', '.join(left_strings)}")

        return namespace

    @staticmethod
    def _split(event: RoomMessageText) -> typing.Iterator[EntityString]:
        """
        Currently unused.

        :param event: event to process
        :type event: nio.RoomMessageText
        :return: list of argument strings
        :rtype: Iterator[EntityString]
        """

        """last_entity = 0

        for entity in msg.entities:
            # If there is normal text left before the next entity
            if last_entity < entity.offset:
                yield from map(EntityString, filter(bool, msg.text[last_entity:entity.offset].split()))

            yield EntityString(msg.text[entity.offset:entity.offset + entity.length], entity)
            last_entity = entity.offset + entity.length

        # Return left over text which might be after the last entity
        if msg.text[last_entity:]:
            yield from map(EntityString, filter(bool, msg.text[last_entity:].split()))"""

        yield from event.stripped_body.split()
