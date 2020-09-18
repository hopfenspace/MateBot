import typing

import telegram

from mate_bot.parsing.util import EntityString, Namespace, Representable


class CommandParser(Representable):

    def parse(self, msg: telegram.Message) -> Namespace:
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
