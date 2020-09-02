#!/usr/bin/env python3

from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters

from config import config
from commands.balance import BalanceCommand
from commands.consume import DrinkCommand
from commands.consume import WaterCommand
from commands.consume import PizzaCommand
from commands.consume import IceCommand
from commands.history import HistoryCommand
from commands.zwegat import ZwegatCommand
from commands.send import SendCommand
from commands.communism import CommunismCommand, communism_query
from commands.pay import PayCommand, pay_query


if __name__ == "__main__":
    updater = Updater(config["bot"]["token"], use_context = True)
    filter_id = Filters.chat(config["chat-id"])

    updater.dispatcher.add_handler(CommandHandler("balance", BalanceCommand()))
    updater.dispatcher.add_handler(CommandHandler("history", HistoryCommand()))
    updater.dispatcher.add_handler(CommandHandler("zwegat", ZwegatCommand()))
    updater.dispatcher.add_handler(CommandHandler("drink", DrinkCommand(), filters=filter_id))
    updater.dispatcher.add_handler(CommandHandler("water", WaterCommand(), filters=filter_id))
    updater.dispatcher.add_handler(CommandHandler("pizza", PizzaCommand(), filters=filter_id))
    updater.dispatcher.add_handler(CommandHandler("ice", IceCommand(), filters=filter_id))
    updater.dispatcher.add_handler(CommandHandler("send", SendCommand(), filters=filter_id))
    updater.dispatcher.add_handler(CommandHandler("communism", CommunismCommand(), filters=filter_id))
    updater.dispatcher.add_handler(CommandHandler("pay", PayCommand(), filters=filter_id))

    updater.dispatcher.add_handler(CallbackQueryHandler(try_wrap(communism_query), pattern="^communism"))
    updater.dispatcher.add_handler(CallbackQueryHandler(try_wrap(pay_query), pattern="^pay"))

    updater.start_polling()
    updater.idle()
