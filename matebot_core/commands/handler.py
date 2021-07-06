"""
MateBot's special Telegram update handler collection
"""

import re
import typing

import telegram.ext


class FilteredChosenInlineResultHandler(telegram.ext.InlineQueryHandler):
    """
    Handler class to filter chosen inline result queries based on patterns for their result IDs

    Note that this handler class does not support the old handler
    API without the CallbackContext parameter. It's primary design
    is to help create more chosen inline result handlers because
    otherwise only one would be supported out of the box.

    :param callback: callback function for this handler that will be called to handle this update
    :type callback: typing.Callable
    :param pattern: optional pattern the result_id of the incoming Update will be checked against
    :type pattern: typing.Union[str, re.Pattern]
    """

    def __init__(self, callback: typing.Callable, pattern: typing.Union[str, re.Pattern] = None):
        super().__init__(callback, pattern=pattern)

    def check_update(self, update: telegram.Update) -> typing.Union[bool, re.Match]:
        """
        Determine whether an update should be passed to this handlers :attr:`callback`

        :param update: incoming Telegram Update
        :type update: telegram.Update
        :return: information to the dispatcher if this handler should handle the update
        :rtype: typing.Union[bool, re.Match]
        """

        if isinstance(update, telegram.Update) and update.chosen_inline_result:
            if not self.pattern:
                return True
            if update.chosen_inline_result.result_id:
                match = re.match(self.pattern, update.chosen_inline_result.result_id)
                if match:
                    return match
        return False
