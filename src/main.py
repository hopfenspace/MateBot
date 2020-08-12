import traceback
from functools import wraps
from typing import Callable
from telegram.ext import Updater, CommandHandler, CallbackQueryHandler, Filters

from config import config
from args import ParsingError

from commands.balance import balance
from commands.consume import drink, water, pizza, ice
from commands.history import history
from commands.zwegat import zwegat
from commands.send import send
from commands.communism import communism, communism_query
from commands.pay import pay, pay_query

updater = Updater(config["bot-token"])
filter_id = Filters.chat(config["chat-id"])


def try_wrap(func: Callable) -> Callable:
    """
    Wrap a function with a try-statement.

    ``ParsingError`` will be ignored, because they are the user's fault and don't need to be logged.
    Any other exception will be caught and printed to stdout for the admin to fix.
    Use this around any command to prevent the bot from stopping if a command is flawed.

    :param func: any function
    :type func: Callable
    :return: exception save function
    :rtype: Callable
    """
    @wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except ParsingError:
            pass
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
