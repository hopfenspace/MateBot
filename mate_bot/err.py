"""
MateBot project-wide exception classes
"""

import logging as _logging
import sys as _sys
import json as _json
import traceback as _traceback

from telegram import Update as _Update, TelegramError
from telegram.ext import CallbackContext as _CallbackContext

from mate_bot.config import config as _config


_logger = _logging.getLogger(__name__)


class MateBotException(Exception):
    """
    Base class for all project-wide exceptions
    """


class DesignViolation(MateBotException):
    """
    Exception when a situation is not intended by design while being a valid state

    This exception is likely to occur when a database operation
    fails due to specific checks. It ensures e.g. that no
    second community user exists in a database or that a user
    is participating in a collective operation at most one time.
    """


class ParsingError(MateBotException):
    """
    Exception raised when the argument parser throws an error

    This is likely to happen when a user messes up the syntax of a
    particular command. Instead of exiting the program, this exception
    will be raised. You may use it's string representation to gain
    additional information about what went wrong. This allows a user
    to correct its command, in case this caused the parser to fail.
    """


class CallbackError(MateBotException):
    """
    Exception raised when parsing or handling callback data throws an error

    This may occur when the callback data does not hold enough information
    to fulfill the desired operation, is of a wrong format or points to
    invalid data (e.g. a payment's callback data points to a communism).
    This type of exception should not happen as it implies serious problems.
    """


def log_error(update: _Update, context: _CallbackContext) -> None:
    """
    Log any error and its traceback to sys.stdout and send it to developers

    :param update: Telegram Update where the error probably occurred
    :type update: telegram.Update
    :param context: context of the error
    :type context: telegram.ext.CallbackContext
    :return: None
    """

    _logger.exception("Something raised an unhandled exception, "
                      "it will be sent to the developers")

    def send_to(env, receiver, text, parse_mode, extra_text = None) -> None:
        try:
            msg = env.bot.send_message(
                receiver, text, parse_mode = parse_mode
            )
            if extra_text is not None:
                msg.reply_text(extra_text, parse_mode=parse_mode, quote=True)
        except TelegramError:
            _logger.exception(f"Error while sending logs to {receiver}:")

    for dev in _config["development"]["notification"]:
        send_to(
            context,
            dev,
            f"Unhandled exception: {_sys.exc_info()[1]}",
            None
        )

    for dev in _config["development"]["description"]:
        send_to(
            context,
            dev,
            f"```\n{_traceback.format_exc()}```",
            "MarkdownV2"
        )

    for dev in _config["development"]["debugging"]:
        send_to(
            context,
            dev,
            f"```\n{_traceback.format_exc()}```",
            "MarkdownV2",
            f"Extended debug information:\n```\n{_json.dumps(update.to_dict(), indent=2, sort_keys=True)}```"
        )
