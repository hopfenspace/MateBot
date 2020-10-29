#!/usr/bin/env python3

import os
import sys
import typing
import logging
import argparse
import unittest

from telegram.ext import (
    Updater, Dispatcher, CommandHandler,
    CallbackQueryHandler, InlineQueryHandler
)

from mate_bot import err, log, registry
from mate_bot.config import config
from mate_bot.commands.handler import FilteredChosenInlineResultHandler
from mate_bot.state.dbhelper import BackendHelper


class _SubcommandHelper:
    """
    Minimal helper class

    :param args: Namespace of parsed arguments
    :type args: argparse.Namespace
    :param logger: logger object that should be used for logging purposes
    :type logger: logging.Logger
    """

    args: argparse.Namespace
    logger: logging.Logger

    def __init__(self, args: argparse.Namespace, logger: logging.Logger):
        self.args = args
        self.logger = logger

    def __call__(self) -> int:
        """
        Execute the main part of the command

        This method is not implemented in this class.
        A subclass should implement this method instead.

        :return: exit code of the feature
        :rtype: int
        """

        raise NotImplementedError


class _Runner(_SubcommandHelper):
    """
    MateBot executor of the ``run`` subcommand
    """

    handler_types = typing.Union[
        typing.Type[CommandHandler],
        typing.Type[CallbackQueryHandler],
        typing.Type[InlineQueryHandler],
        typing.Type[FilteredChosenInlineResultHandler]
    ]

    def __call__(self) -> int:
        """
        Execute the main part of the ``run`` command

        :return: exit code of the feature
        :rtype: int
        """

        if self.args.pid:
            print(f"MateBot process ID: {os.getpid()}")
            self.logger.debug(f"Running in process ID {os.getpid()}")

        if not self.args.silent:
            BackendHelper._query_logger = logging.getLogger("database")

        self.logger.info("Checking database connection...")
        BackendHelper.db_config = config["database"]
        BackendHelper.get_value("users")

        self.logger.debug("Creating Updater...")
        updater = Updater(config["token"], use_context = True)

        self.logger.info("Adding error handler...")
        updater.dispatcher.add_error_handler(err.log_error)

        self.add_handler(updater.dispatcher, CommandHandler, registry.commands, False)
        self.add_handler(updater.dispatcher, CallbackQueryHandler, registry.callback_queries, True)
        self.add_handler(updater.dispatcher, InlineQueryHandler, registry.inline_queries, True)
        self.add_handler(updater.dispatcher, FilteredChosenInlineResultHandler, registry.inline_results, True)

        self.logger.info("Starting bot...")
        updater.start_polling()
        updater.idle()

        return 0

    def add_handler(
            self,
            dispatcher: Dispatcher,
            handler: handler_types,
            pool: dict,
            pattern: bool = True
    ) -> None:
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

        self.logger.info(f"Adding {handler.__name__} executors...")
        for name in pool:
            if pattern:
                dispatcher.add_handler(handler(pool[name], pattern = name))
            else:
                dispatcher.add_handler(handler(name, pool[name]))


class _Installer(_SubcommandHelper):
    """
    MateBot executor of the ``install`` subcommand
    """

    def __call__(self) -> int:
        """
        Execute the main part of the ``install`` command

        :return: exit code of the feature
        :rtype: int
        """

        if not self.args.no_config_check:
            self.check_config()
        if not self.args.no_testing:
            self.check_unittests()
        if not self.args.no_database:
            self.install_database()

        return 0

    def check_config(self) -> None:
        """
        Check the configuration file for syntax errors and valid values

        :return: None
        """

        raise NotImplementedError

    def check_unittests(self) -> None:
        """
        Check the code base by performing the unittest framework

        :return: None
        """

        import test

        verbosity = 1
        if self.args.verbose:
            verbosity = 2

        loader = unittest.loader.TestLoader()
        loader.suiteClass = test.SortedTestSuite
        unittest.main("test", argv=[sys.argv[0]], exit=False, verbosity=verbosity, testLoader=loader)

    def install_database(self) -> None:
        """
        Install the database and setup the necessary tables

        .. note::

            The user and permissions to interact with the database
            must be configured before this feature can work. The
            database users' credentials must be stored in the config file.

        :return: None
        """

        self.logger.warning("Installing database... This may overwrite existing data!")
        BackendHelper.rebuild_database()


class _Extractor(_SubcommandHelper):
    """
    MateBot executor of the ``extract`` subcommand
    """

    def __call__(self) -> int:
        """
        Execute the main part of the ``extract`` command

        :return: exit code of the feature
        :rtype: int
        """

        pass


class MateBot:
    """
    MateBot application executor

    :param args: parsed program arguments as returned by ``parse_args``
    :type args: argparse.Namespace
    """

    _args: argparse.Namespace

    def __init__(self, args: argparse.Namespace):
        self._args = args

        if self._args.silent:
            self.logger = logging.getLogger()
            self.logger.addHandler(logging.NullHandler())
        else:
            log.setup()
            self.logger = logging.getLogger("runner")

        self.run = _Runner(args, self.logger)
        self.install = _Installer(args, self.logger)
        self.extract = _Extractor(args, self.logger)

        self.logger.debug(f"Created  {self}.")

    def start(self) -> int:
        """
        Start the runner to execute the programs to handle the specified arguments

        :return: program exit code
        :rtype: int
        """

        command = getattr(self, self._args.command)
        self.logger.debug(f"Calling {command}...")
        code = command()
        self.logger.info(f"Finished with exit code {code}.")
        return code

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
            "-s", "--silent",
            help = "disable logging to log files",
            dest = "silent",
            action = "store_true"
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

        run.add_argument(
            "-p", "--pid",
            help = "print the process ID after startup",
            dest = "pid",
            action = "store_true"
        )

        install = subcommands.add_parser(
            "install",
            help = "install the MateBot database and systemd service files"
        )

        install.add_argument(
            "-c", "--no-config-check",
            help = "do not check the config file",
            dest = "no_config_check",
            action = "store_true"
        )

        install.add_argument(
            "-d", "--no-database",
            help = "do not touch the database",
            dest = "no_database",
            action = "store_true"
        )

        install.add_argument(
            "-t", "--no-test",
            help = "do not run unittests before installing",
            dest = "no_testing",
            action = "store_true"
        )

        extract = subcommands.add_parser(
            "extract",
            help = "extract the raw data from the MateBot database"
        )

        return parser


if __name__ == "__main__":
    arguments = MateBot.setup().parse_args()
    exit(MateBot(arguments).start())
