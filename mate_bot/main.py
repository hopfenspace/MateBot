#!/usr/bin/env python3

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters

import err
from config import config

from commands.balance import BalanceCommand
from commands.communism import CommunismCommand, CommunismQuery
from commands.consume import dynamic_consumable
from commands.data import DataCommand
from commands.help import HelpCommand
from commands.history import HistoryCommand
#from commands.pay import PayCommand, PayQuery
from commands.send import SendCommand
from commands.start import StartCommand
from commands.blame import BlameCommand


if __name__ == "__main__":
    updater = Updater(config["bot"]["token"], use_context = True)
    internal_filter = Filters.chat(config["bot"]["chat"])

    updater.dispatcher.add_handler(CommandHandler("balance", BalanceCommand()))
    updater.dispatcher.add_handler(CommandHandler("communism", CommunismCommand()))
    updater.dispatcher.add_handler(CommandHandler("data", DataCommand()))
    updater.dispatcher.add_handler(CommandHandler("help", HelpCommand()))
    updater.dispatcher.add_handler(CommandHandler("history", HistoryCommand()))
#    updater.dispatcher.add_handler(CommandHandler("pay", PayCommand()))
    updater.dispatcher.add_handler(CommandHandler("send", SendCommand()))
    updater.dispatcher.add_handler(CommandHandler("start", StartCommand()))
    updater.dispatcher.add_handler(CommandHandler("blame", BlameCommand()))

    for consumable in config["consumables"]:
        updater.dispatcher.add_handler(CommandHandler(consumable["name"], dynamic_consumable(consumable)()))

    updater.dispatcher.add_handler(CallbackQueryHandler(CommunismQuery(), pattern="^communism"))
#    updater.dispatcher.add_handler(CallbackQueryHandler(PayQuery(), pattern="^pay"))

    updater.dispatcher.add_error_handler(err.log_error)

    updater.start_polling()
    updater.idle()
