#!/usr/bin/env python3

import logging
import argparse

from telegram.ext import (
    Updater, CommandHandler,
    CallbackQueryHandler,
    ChosenInlineResultHandler,
    Filters, InlineQueryHandler
)


from mate_bot import err
from mate_bot import log
from mate_bot.config import config
from mate_bot.commands.registry import COMMANDS
from mate_bot.commands.communism import (
    CommunismCallbackQuery,
    CommunismInlineQuery,
    CommunismInlineResult
)
from mate_bot.commands.send import SendCallbackQuery


class MateBotRunner:
    """
    MateBot application executor
    """

    def __init__(self, args: argparse.Namespace) -> None:
        pass

    @staticmethod
    def setup() -> argparse.ArgumentParser:
        """
        Setup the ArgumentParser to provide the command-line interface

        :return: ArgumentParser
        :rtype: argparse.ArgumentParser
        """

        parser = argparse.ArgumentParser(
            description = "MateBot maintaining command-line interface"
        )

        parser.add_argument(
            "-v", "--verbose",
            help = "print out verbose information",
            dest = "verbose",
            action = "store_true"
        )

        subcommands = parser.add_subparsers(
            title = "available subcommands",
            dest = "command",
            required = True
        )

        run = subcommands.add_parser(
            "run",
            help = "run the MateBot program"
        )

        install = subcommands.add_parser(
            "install",
            help = "install the MateBot database and systemd service files"
        )

        database.add_argument(
            "-s", "--show",
            help = "show all data stored in the specified table",
            dest = "data",
            metavar = "table"
        )

        extract = subcommands.add_parser(
            "extract",
            help = "extract the raw data from the MateBot database"
        )

        return parser


COMMANDS = {
    Filters.all: COMMANDS.commands_as_dict
}

HANDLERS = {
    CallbackQueryHandler: {
        "^communism": CommunismCallbackQuery(),
        # "^pay": PayQuery(),
        "^send": SendCallbackQuery()
    },
    InlineQueryHandler: {
        "": CommunismInlineQuery()
    }
}


if __name__ == "__main__":
    arguments = MateBotRunner.setup().parse_args()
    exit(MateBotRunner(arguments).start())

    log.setup()
    logger = logging.getLogger()

    updater = Updater(config["bot"]["token"], use_context = True)
    internal_filter = Filters.chat(config["bot"]["chat"])

    logger.info("Adding error handler...")
    updater.dispatcher.add_error_handler(err.log_error)

    logger.info("Adding command handlers...")
    for cmd_filter, commands in COMMANDS.items():
        for name, cmd in commands.items():
            updater.dispatcher.add_handler(
                CommandHandler(name, cmd, filters=cmd_filter)
            )

    logger.info("Adding other handlers...")
    updater.dispatcher.add_handler(ChosenInlineResultHandler(CommunismInlineResult()))
    for handler in HANDLERS:
        for pattern in HANDLERS[handler]:
            updater.dispatcher.add_handler(handler(HANDLERS[handler][pattern], pattern=pattern))

    logger.info("Starting bot...")
    updater.start_polling()
    updater.idle()
