#!/usr/bin/env python3

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters

from config import config

from commands.balance import BalanceCommand
from commands.communism import CommunismCommand, CommunismQuery
from commands.consume import DrinkCommand, IceCommand, PizzaCommand, WaterCommand
from commands.data import DataCommand
from commands.help import HelpCommand
from commands.history import HistoryCommand
#from commands.pay import PayCommand, PayQuery
from commands.send import SendCommand
from commands.start import StartCommand


if __name__ == "__main__":
    updater = Updater(config["bot"]["token"], use_context = True)
    internal_filter = Filters.chat(config["bot"]["chat"])

    updater.dispatcher.add_handler(CommandHandler("balance", BalanceCommand()))
    updater.dispatcher.add_handler(CommandHandler("communism", CommunismCommand()))
    updater.dispatcher.add_handler(CommandHandler("drink", DrinkCommand()))
    updater.dispatcher.add_handler(CommandHandler("ice", IceCommand()))
    updater.dispatcher.add_handler(CommandHandler("pizza", PizzaCommand()))
    updater.dispatcher.add_handler(CommandHandler("water", WaterCommand()))
    updater.dispatcher.add_handler(CommandHandler("data", DataCommand()))
    updater.dispatcher.add_handler(CommandHandler("help", HelpCommand()))
    updater.dispatcher.add_handler(CommandHandler("history", HistoryCommand()))
#    updater.dispatcher.add_handler(CommandHandler("pay", PayCommand()))
    updater.dispatcher.add_handler(CommandHandler("send", SendCommand()))
    updater.dispatcher.add_handler(CommandHandler("start", StartCommand()))

    updater.dispatcher.add_handler(CallbackQueryHandler(CommunismQuery(), pattern="^communism"))
#    updater.dispatcher.add_handler(CallbackQueryHandler(PayQuery(), pattern="^pay"))

    updater.start_polling()
    updater.idle()
