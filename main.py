#!/usr/bin/env python3

import logging

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters

from mate_bot import err
from mate_bot import log
from mate_bot.config import config
from mate_bot.commands.balance import BalanceCommand
from mate_bot.commands.communism import CommunismCommand, CommunismQuery
from mate_bot.commands.consume import dynamic_consumable
from mate_bot.commands.data import DataCommand
from mate_bot.commands.help import HelpCommand
from mate_bot.commands.history import HistoryCommand
#from mate_bot.commands.pay import PayCommand, PayQuery
from mate_bot.commands.send import SendCommand
from mate_bot.commands.start import StartCommand
from mate_bot.commands.blame import BlameCommand
from mate_bot.commands.zwegat import ZwegatCommand


if __name__ == "__main__":
    log.setup()
    logger = logging.getLogger()

    updater = Updater(config["bot"]["token"], use_context = True)
    internal_filter = Filters.chat(config["bot"]["chat"])

    updater.dispatcher.add_error_handler(err.log_error)

    logger.info("Adding the CommandHandlers")

    updater.dispatcher.add_handler(CommandHandler("balance", BalanceCommand()))
    updater.dispatcher.add_handler(CommandHandler("communism", CommunismCommand()))
    updater.dispatcher.add_handler(CommandHandler("data", DataCommand()))
    updater.dispatcher.add_handler(CommandHandler("help", HelpCommand()))
    updater.dispatcher.add_handler(CommandHandler("history", HistoryCommand()))
#    updater.dispatcher.add_handler(CommandHandler("pay", PayCommand()))
    updater.dispatcher.add_handler(CommandHandler("send", SendCommand()))
    updater.dispatcher.add_handler(CommandHandler("start", StartCommand()))
    updater.dispatcher.add_handler(CommandHandler("blame", BlameCommand()))
    updater.dispatcher.add_handler(CommandHandler("zwegat", ZwegatCommand()))
    updater.dispatcher.add_handler(CallbackQueryHandler(CommunismQuery(), pattern="^communism"))
    #    updater.dispatcher.add_handler(CallbackQueryHandler(PayQuery(), pattern="^pay"))

    logger.info("Adding the custom consumables")

    for consumable in config["consumables"]:
        updater.dispatcher.add_handler(CommandHandler(consumable["name"], dynamic_consumable(consumable)()))

    logger.info("Start bot")

    updater.start_polling()
    updater.idle()
