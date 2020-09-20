#!/usr/bin/env python3

import logging

from telegram.ext import (
    Updater, CommandHandler,
    CallbackQueryHandler,
    ChosenInlineResultHandler,
    Filters, InlineQueryHandler,
    MessageHandler
)


from mate_bot import err
from mate_bot import log
from mate_bot.config import config
from mate_bot.commands.balance import BalanceCommand
from mate_bot.commands.communism import (
    CommunismCommand, CommunismCallbackQuery,
    CommunismInlineQuery, CommunismInlineResult
)
from mate_bot.commands.consume import dynamic_consumable
from mate_bot.commands.data import DataCommand
from mate_bot.commands.help import HelpCommand
from mate_bot.commands.history import HistoryCommand
# from mate_bot.commands.pay import PayCommand, PayQuery
from mate_bot.commands.send import SendCommand
from mate_bot.commands.start import StartCommand
from mate_bot.commands.blame import BlameCommand
from mate_bot.commands.vouch import VouchCommand
from mate_bot.commands.zwegat import ZwegatCommand


COMMANDS = {
    Filters.all: {
        "balance": BalanceCommand(),
        "communism": CommunismCommand(),
        "data": DataCommand(),
        "help": HelpCommand(),
        "history": HistoryCommand(),
        # "pay": PayCommand(),
        "send": SendCommand(),
        "start": StartCommand(),
        "blame": BlameCommand(),
        "vouch": VouchCommand(),
        "zwegat": ZwegatCommand()
    }
}

HANDLERS = {
    CallbackQueryHandler: {
        "^communism": CommunismCallbackQuery(),
        # "^pay": PayQuery()
    },
    InlineQueryHandler: {
        "": CommunismInlineQuery()
    }
}


if __name__ == "__main__":
    log.setup()
    logger = logging.getLogger()

    updater = Updater(config["bot"]["token"], use_context = True)
    internal_filter = Filters.chat(config["bot"]["chat"])

    logger.info("Adding error handler...")
    updater.dispatcher.add_error_handler(err.log_error)

    logger.info("Adding command handlers...")
    for filter_ in COMMANDS:
        for name in COMMANDS[filter_]:
            updater.dispatcher.add_handler(
                CommandHandler(name, COMMANDS[filter_][name], filters=filter_)
            )
    for consumable in config["consumables"]:
        updater.dispatcher.add_handler(CommandHandler(consumable["name"], dynamic_consumable(consumable)()))

    logger.info("Adding other handlers...")
    updater.dispatcher.add_handler(ChosenInlineResultHandler(CommunismInlineResult()))
    for handler in HANDLERS:
        for pattern in HANDLERS[handler]:
            updater.dispatcher.add_handler(handler(HANDLERS[handler][pattern], pattern=pattern))

    logger.info("Starting bot...")
    updater.start_polling()
    updater.idle()
