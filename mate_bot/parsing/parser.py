import typing

import telegram

from mate_bot.err import ParsingError
from mate_bot.parsing.util import EntityString, Namespace, Representable
from mate_bot.parsing.usage import CommandUsage
from mate_bot.parsing.actions import Action


class CommandParser(Representable):

    def __init__(self):
        # Add initial default usage
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

    def parse(self, msg: telegram.Message) -> Namespace:
        """
        Parse a telegram message into a namespace.

        :param msg: message to parse
        :type msg: telegram.Message
        :return: parsed arguments
        :rtype: Namespace
        """
        arg_strings = list(self._split(msg))
        pass

    @staticmethod
    def _split(msg: telegram.Message) -> typing.Iterator[typing.Union[str, EntityString]]:
        """
        Split a telegram message into EntityStrings

        This functions splits by spaces while keeping entities intact.

        Danger!!!
        Nested entities would probably break this.
        """
        last_entity = 0

        for entity in msg.entities:
            # If there is normal text left before the next entity
            if last_entity < entity.offset:
                yield from map(EntityString, filter(bool, reversed(msg.text[last_entity:entity.offset].split())))

            yield EntityString(msg.text[entity.offset:entity.offset + entity.length], entity)
            last_entity = entity.offset + entity.length

        # Return left over text which might be after the last entity
        if msg.text[last_entity:]:
            yield from map(EntityString, filter(bool, reversed(msg.text[last_entity:].split())))
