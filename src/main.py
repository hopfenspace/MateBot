import traceback
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters

from config import config

from commands.balance import balance
from commands.consume import drink, water, pizza, ice
from commands.history import history
from commands.zwegat import zwegat
from commands.send import send
from commands.communism import communism, communism_query
from commands.pay import pay, pay_query

updater = Updater(config["bot-token"])
filter_id = Filters.chat(config["chat-id"])


def try_wrap(func):
    def wrapper(*args, **kwargs):
        try:
            func(*args, **kwargs)
        except:
            print(traceback.format_exc())

    return wrapper


updater.dispatcher.add_handler(CommandHandler("balance", try_wrap(balance)))
updater.dispatcher.add_handler(CommandHandler("history", try_wrap(history)))
updater.dispatcher.add_handler(CommandHandler("zwegat", try_wrap(zwegat)))
updater.dispatcher.add_handler(CommandHandler("drink", try_wrap(drink), filters=filter_id))
updater.dispatcher.add_handler(CommandHandler("water", try_wrap(water), filters=filter_id))
updater.dispatcher.add_handler(CommandHandler("pizza", try_wrap(pizza), filters=filter_id))
updater.dispatcher.add_handler(CommandHandler("ice", try_wrap(ice), filters=filter_id))
updater.dispatcher.add_handler(CommandHandler("send", try_wrap(send), filters=filter_id))
updater.dispatcher.add_handler(CommandHandler("communism", try_wrap(communism), filters=filter_id))
updater.dispatcher.add_handler(CommandHandler("pay", try_wrap(pay), filters=filter_id))

updater.dispatcher.add_handler(CallbackQueryHandler(try_wrap(communism_query), pattern="^communism"))
updater.dispatcher.add_handler(CallbackQueryHandler(try_wrap(pay_query), pattern="^pay"))

updater.start_polling()
updater.idle()
