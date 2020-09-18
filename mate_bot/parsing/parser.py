import typing
from argparse import Namespace
from argparse import _AttributeHolder

import telegram

from mate_bot.parsing.string import EntityString


class CommandParser(_AttributeHolder):

    def parse(self, msg: telegram.Message) -> Namespace:
        arg_strings = self._split(msg)
        pass

    @staticmethod
    def _split_by_entities(msg: telegram.Message) -> typing.Iterator[typing.Union[str, EntityString]]:
        """
        Split a telegram message by its entities.

        All entities will become a separate piece and the raw text in between entities.
        This iterator will give the split pieces in reverse order!

        Danger!!!
        Nested entities would probably break this.
        """
        text = msg.text

        for entity in reversed(msg.entities):
            # If there is normal text left after the entity
            if entity.offset + entity.length < len(text):
                yield text[entity.offset + entity.length:]
                # Oneliner potentially replacing _split
                # yield from map(EntityString, filter(bool, text[entity.offset + entity.length:].split()))
                text = text[:entity.offset + entity.length]

            yield EntityString(text[entity.offset:], entity)
            text = text[:entity.offset]

        # Return left over text which might be before any entities
        if text:
            yield text

    def _split(self, msg: telegram.Message) -> typing.List[EntityString]:
        """
        Split a telegram message into EntityStrings

        This functions splits by spaces while keeping entities intact.
        """
        result = []

        for string in self._split_by_entities(msg):
            # strings which contain entities remain untouched
            if isinstance(string, EntityString):
                result.append(string)

            # strings which don't contain entities will be split by spaces
            else:
                for piece in string.split():
                    if piece:
                        result.append(EntityString(piece, None))

        return reversed(result)
