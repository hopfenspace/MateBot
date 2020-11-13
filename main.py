#!/usr/bin/env python3

import os
import sys
import json
import typing
import argparse
import datetime
import unittest
import logging.config

import pymysql.err
import telegram.ext

from mate_bot import err
from mate_bot import registry
from mate_bot.state.dbhelper import BackendHelper
from mate_bot.commands.handler import FilteredChosenInlineResultHandler


class NoDebugFilter(logging.Filter):
    """
    Logging filter that filters out any DEBUG message for the specified logger or handler
    """

    def filter(self, record: logging.LogRecord) -> int:
        if super().filter(record):
            return record.levelno > logging.DEBUG
        return True


class _SubcommandHelper:
    """
    Minimal helper class

    :param args: Namespace of parsed arguments
    :type args: argparse.Namespace
    """

    args: argparse.Namespace
    logger: logging.Logger
    _config: typing.Optional[dict]

    def __init__(self, args: argparse.Namespace):
        self.args = args
        self._config = None

    def __call__(self, logger: logging.Logger) -> int:
        """
        Execute the main part of the command

        This method is not implemented in this class.
        A subclass should implement this method instead.

        :param logger: logger object that should be set as instance
            attribute before the command is executed
        :type logger: logging.Logger
        :return: exit code of the feature
        :rtype: int
        """

        raise NotImplementedError

    @property
    def config(self) -> typing.Optional[dict]:
        """
        Get a copy of the MateBot configuration
        """

        if self._config is None:
            self.logger.info("Attempting to import configuration files...")
            import mate_bot.config
            self._config = mate_bot.config.config
            self.logger.info("Imported configuration successfully.")
        return self._config.copy()

    def setup_database(self):
        """
        Setup the database configuration in the :class:`mate_bot.state.dbhelper.BackendHelper`
        """

        if not self.args.silent:
            BackendHelper.query_logger = logging.getLogger("database")

        self.logger.info("Checking database connection...")
        BackendHelper.db_config = self.config["database"]
        BackendHelper.get_value("users")

    def print(self, *args, **kwargs) -> None:
        """
        Print to the console and log to logfiles as well

        :param args: any positional arguments
        :param kwargs: any keyword arguments
        :return: None
        """

        print(*args, **kwargs)

        sep = " "
        if "sep" in kwargs:
            sep = kwargs["sep"]

        if "file" in kwargs and kwargs["file"] == sys.stderr:
            self.logger.error(sep.join(args))
        else:
            self.logger.info(sep.join(args))


class _Runner(_SubcommandHelper):
    """
    MateBot executor of the ``run`` subcommand
    """

    handler_types = typing.Union[
        typing.Type[telegram.ext.CommandHandler],
        typing.Type[telegram.ext.CallbackQueryHandler],
        typing.Type[telegram.ext.InlineQueryHandler],
        typing.Type[FilteredChosenInlineResultHandler]
    ]

    def __call__(self, logger: logging.Logger) -> int:
        """
        Execute the main part of the ``run`` command

        :param logger: logger object that should be set as instance
            attribute before the command is executed
        :type logger: logging.Logger
        :return: exit code of the feature
        :rtype: int
        """

        self.logger = logger

        if self.args.pid:
            print(f"MateBot process ID: {os.getpid()}")
            self.logger.debug(f"Running in process ID {os.getpid()}")

        self.setup_database()

        self.logger.debug("Creating Updater...")
        updater = telegram.ext.Updater(self.config["token"], use_context = True)

        self.logger.info("Adding error handler...")
        updater.dispatcher.add_error_handler(err.log_error)

        self.add_handler(updater.dispatcher, telegram.ext.CommandHandler, registry.commands, False)
        self.add_handler(updater.dispatcher, telegram.ext.CallbackQueryHandler, registry.callback_queries, True)
        self.add_handler(updater.dispatcher, telegram.ext.InlineQueryHandler, registry.inline_queries, True)
        self.add_handler(updater.dispatcher, FilteredChosenInlineResultHandler, registry.inline_results, True)

        self.logger.info("Starting bot...")
        updater.start_polling()
        updater.idle()

        return 0

    def add_handler(
            self,
            dispatcher: telegram.ext.Dispatcher,
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


class _Manager(_SubcommandHelper):
    """
    MateBot executor of the ``manage`` subcommand
    """

    def __call__(self, logger: logging.Logger) -> int:
        """
        Execute the main part of the ``manage`` command

        :param logger: logger object that should be set as instance
            attribute before the command is executed
        :type logger: logging.Logger
        :return: exit code of the feature
        :rtype: int
        """

        self.logger = logger

        return 0

    @staticmethod
    def get_user(name: str) -> typing.Optional[MateBotUser]:
        """
        Return the MateBot user found for the given name (which might be a user ID as well)

        :param name: unique user ID or unambiguous username to identify a user
        :type name: str
        :return: the only MateBot user found or None
        :rtype: typing.Optional[MateBotUser]
        """

        if name.isdigit():
            number = int(name)
            uid = MateBotUser.get_uid_from_tid(number)
            if uid is None:
                try:
                    return MateBotUser(number)
                except pymysql.err.DataError:
                    pass

        else:
            targets = find_user_by_name(name), find_user_by_username(name)
            if all(targets) or not any(targets):
                targets = find_user_by_name(name, True), find_user_by_username(name, True)
            if all(targets) or not any(targets):
                return
            return list(filter(lambda x: x is not None, targets))[0]


class _Installer(_SubcommandHelper):
    """
    MateBot executor of the ``install`` subcommand
    """

    def __call__(self, logger: logging.Logger) -> int:
        """
        Execute the main part of the ``install`` command

        :param logger: logger object that should be set as instance
            attribute before the command is executed
        :type logger: logging.Logger
        :return: exit code of the feature
        :rtype: int
        """

        self.logger = logger

        if not self.args.no_config_check:
            self.check_config()
        if not self.args.no_testing:
            self.check_unittests()
        self.setup_database()
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

        self.print("Installing database... This may overwrite existing data!", file = sys.stderr)
        BackendHelper.rebuild_database()


class _Extractor(_SubcommandHelper):
    """
    MateBot executor of the ``extract`` subcommand
    """

    def __call__(self, logger: logging.Logger) -> int:
        """
        Execute the main part of the ``extract`` command

        :param logger: logger object that should be set as instance
            attribute before the command is executed
        :type logger: logging.Logger
        :return: exit code of the feature
        :rtype: int
        """

        self.logger = logger

        self.setup_database()

        extraction = BackendHelper.extract_all(self.args.ignore_schema)
        if self.args.raw:
            result = str(extraction)

        else:
            for table in extraction:
                data = extraction[table]
                for entry in data:
                    for k in entry:
                        if isinstance(entry[k], datetime.datetime):
                            entry[k] = int(entry[k].timestamp())

            result = json.dumps(extraction, indent = 4, sort_keys = True)

        if self.args.output:
            if os.path.exists(self.args.output) and not self.args.force:
                self.print(
                    f"File '{self.args.output}' already exists. "
                    f"It will not be overwritten unless -f is given.",
                    file = sys.stderr
                )
            else:
                with open(self.args.output, "w") as f:
                    f.write(result)

        else:
            print(result)

        return 0


class MateBot:
    """
    MateBot application executor

    :param args: optional parsed program arguments as returned by ``parse_args``
    :type args: typing.Optional[argparse.Namespace]
    """

    _args: typing.Optional[argparse.Namespace]

    run: _Runner
    manage: _Manager
    install: _Installer
    extract: _Extractor

    def __init__(self, args: typing.Optional[argparse.Namespace] = None):
        if args is None:
            args = MateBot.setup().parse_args()
        self._args = args

        self.run = _Runner(args)
        self.manage = _Manager(args)
        self.install = _Installer(args)
        self.extract = _Extractor(args)

    def start(self, configuration: dict) -> int:
        """
        Start the runner to execute the programs to handle the specified arguments

        :param configuration: configuration dictionary as loaded e.g. by a ``json.load``
        :type configuration: dict
        :return: program exit code
        :rtype: int
        """

        if self._args.silent:
            logger = logging.getLogger()
            logger.addHandler(logging.NullHandler())
        else:
            logging.config.dictConfig(configuration["logging"])
            for handler in logging.root.handlers:
                handler.addFilter(NoDebugFilter("telegram"))
            logger = logging.getLogger("runner")

        command = getattr(self, self._args.command, NotImplemented)
        logger.debug(f"Calling {command}...")
        code = command(logger)
        logger.info(f"Finished with exit code {code}.")
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

        manage = subcommands.add_parser(
            "manage",
            help = "manage MateBot data for its users"
        )

        manage.add_argument(
            "-b", "--balance",
            help = "get the current account balance",
            action = "store_true"
        )

        manage.add_argument(
            "-p", "--permission",
            help = "get or set the permission flag of the user",
            choices = ("allow", "deny", "get")
        )

        manage.add_argument(
            "user",
            help = "internal user ID, user's Telegram ID or unambiguous username",
            nargs = "+"
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

        extract.add_argument(
            "-f", "--force",
            help = "allow overwriting existing files",
            dest = "force",
            action = "store_true"
        )

        extract.add_argument(
            "-i", "--ignore",
            help = "disable the strict schema checks and extract everything",
            dest = "ignore_schema",
            action = "store_true"
        )

        extract.add_argument(
            "-o", "--output",
            help = "filename the data should be written to",
            dest = "output",
            default = ""
        )

        extract.add_argument(
            "-r", "--raw",
            help = "output the raw data without converting data to valid JSON",
            dest = "raw",
            action = "store_true"
        )

        return parser


if __name__ == "__main__":
    runner = MateBot()
    from mate_bot.config import config
    exit(runner.start(config))
