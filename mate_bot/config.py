"""
MateBot configuration provider
"""
import logging.config

from hopfenmatrix.config import Config, Namespace


class MateBotConfig(Config):

    def __init__(self):
        super(MateBotConfig, self).__init__()

        self.general = Namespace()
        self.general.max_amount = 10000
        self.general.max_consume = 10
        self.general.db_localtime = False

        self.room = ""

        self.community = Namespace()
        self.community.payment_consent = 2
        self.community.payment_denial = 2
        self.community.multiple_externals = True

        self.database = Namespace()
        self.database.host = "localhost"
        self.database.port = 3306
        self.database.db = "mate_db"
        self.database.user = "matebot_user"
        self.database.password = "password"
        self.database.charset = "utf8mb4"

        self.testing = Namespace()
        self.testing.db = "mate_db_test"

        self.logging = Namespace()
        self.logging.version = 1
        self.logging.disable_existing_loggers = True
        self.logging.incremental = False

        self.logging.root = Namespace()
        self.logging.root.level = "DEBUG"
        self.logging.root.handlers = ["console", "file"]

        self.logging.formatters = Namespace()
        self.logging.handlers = Namespace()
        self.logging.formatters.console = {
            "style": "{",
            "class": "logging.Formatter",
            "format": "{asctime}: MateBot {process}: [{levelname}] {name}: {message}",
            "datefmt": "%d.%m.%Y %H:%M"
        }
        self.logging.formatters.file = {
            "style": "{",
            "class": "logging.Formatter",
            "format": "matebot {process}: [{levelname}] {name}: {message}",
            "datefmt": "%d.%m.%Y %H:%M"
        }
        self.logging.handlers.console = {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "formatter": "console",
            "stream": "ext://sys.stdout"
        }
        self.logging.handlers.file = {
            "level": "DEBUG",
            "class": "logging.handlers.WatchedFileHandler",
            "formatter": "file",
            "filename": "matebot.log",
            "encoding": "UTF-8"
        }

        self.logging.loggers = Namespace()
        self.logging.loggers.collectives = {}
        self.logging.loggers.commands = {}
        self.logging.loggers.config = {}
        self.logging.loggers.database = {}
        self.logging.loggers.error = {}
        self.logging.loggers.state = {}

        self.consumables = [
            {
                "name": "drink",
                "description": "",
                "price": 100,
                "messages": [
                    "Okay, enjoy your "
                ],
                "symbol": "\uD83E\uDDC9"
            },
            {
                "name": "water",
                "description": "",
                "price": 50,
                "messages": [
                    "HYDRATION! ",
                    "Hydrier dich mit ",
                    "Hydrieren sie sich bitte mit ",
                    "Der Bahnbabo sagt: Hydriert euch mit ",
                    "Okay, enjoy your "
                ],
                "symbol": "\uD83D\uDCA7"
            },
            {
                "name": "pizza",
                "description": "",
                "price": 200,
                "messages": [
                    "Okay, enjoy your ",
                    "Buon appetito! "
                ],
                "symbol": "\uD83C\uDF55"
            },
            {
                "name": "ice",
                "description": "",
                "price": 50,
                "messages": [
                    "Okay, enjoy your ",
                    "Hmmh, yummy... "
                ],
                "symbol": "\uD83C\uDF68"
            }
        ]

    def setup_logging(self):
        logging.config.dictConfig(self.logging)


config = MateBotConfig.from_json("config.json")
