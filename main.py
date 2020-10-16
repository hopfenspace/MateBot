#!/usr/bin/env python3

import typing
import logging

from telegram.ext import (
    Updater, Dispatcher, CommandHandler,
    CallbackQueryHandler, InlineQueryHandler
)

from mate_bot import err
from mate_bot import log
from mate_bot import registry
from mate_bot.config import config
from mate_bot.commands.handler import FilteredChosenInlineResultHandler
from mate_bot.state.dbhelper import BackendHelper


handler_types = typing.Union[
    typing.Type[CommandHandler],
    typing.Type[CallbackQueryHandler],
    typing.Type[InlineQueryHandler],
    typing.Type[FilteredChosenInlineResultHandler]
]


def _add(dispatcher: Dispatcher, handler: handler_types, pool: dict, pattern: bool = True) -> None:
    """
    Add the executors from the given pool to the dispatcher using the given handler type

    :param dispatcher: Telegram's dispatcher to add the executor to
    :type dispatcher: telegram.ext.Dispatcher
    :param handler: type of the handler (subclass of ``telegram.ext.Handler``)
    :type handler: handler_types
    :param pool: collection of all executors for one handler type
    :type pool: dict
    :param pattern: switch whether the keys of the pool are patterns or names
    :type pattern: bool
    :return: None
    """

    logger.info(f"Adding {handler.__name__} executors...")
    for name in pool:
        if pattern:
            dispatcher.add_handler(handler(pool[name], pattern=name))
        else:
            dispatcher.add_handler(handler(name, pool[name]))


if __name__ == "__main__":
    log.setup()
    logger = logging.getLogger()
    BackendHelper._query_logger = logging.getLogger("database")

    updater = Updater(config["token"], use_context = True)

    logger.info("Adding error handler...")
    updater.dispatcher.add_error_handler(err.log_error)

    _add(updater.dispatcher, CommandHandler, registry.commands, False)
    _add(updater.dispatcher, CallbackQueryHandler, registry.callback_queries, True)
    _add(updater.dispatcher, InlineQueryHandler, registry.inline_queries, True)
    _add(updater.dispatcher, FilteredChosenInlineResultHandler, registry.inline_results, True)

    logger.info("Starting bot...")
    updater.start_polling()
    updater.idle()
