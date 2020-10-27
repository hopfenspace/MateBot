"""
MateBot testing suite
"""

import sys
import unittest


class EnvironmentTests(unittest.TestCase):
    """
    Testing suite for the environment the MateBot is running in
    """

    def test_os(self):
        self.assertEqual(sys.platform, "linux")

    def test_py_version(self):
        self.assertEqual(sys.version_info.major, 3)
        self.assertGreaterEqual(sys.version_info.minor, 7)

    @staticmethod
    def test_imports():
        import pytz
        import tzlocal
        import telegram
        import pymysql
        del pytz, tzlocal, telegram, pymysql

    def test_config(self):
        from mate_bot.config import config

        mandatory_keys = [
            ("general", dict),
            ("token", str),
            ("chats", dict),
            ("community", dict),
            ("database", dict),
            ("consumables", list)
        ]

        for k in mandatory_keys:
            self.assertIn(k[0], config)
            self.assertIsInstance(config[k[0]], k[1])

        mandatory_subkeys = [
            ("general:max-amount", int),
            ("general:max-consume", int),
            ("chats:internal", int),
            ("community:payment-consent", int),
            ("community:payment-denial", int),
            ("database:host", str),
            ("database:db", str),
            ("database:user", str),
            ("database:password", str)
        ]

        for k in mandatory_subkeys:
            first, second = k[0].split(":")
            self.assertIn(second, config[first])
            self.assertIsInstance(config[first][second], k[1])

        mandatory_consumable_keys = [
            ("name", str),
            ("description", str),
            ("price", int),
            ("messages", list),
            ("symbol", str)
        ]

        for consumable in config["consumables"]:
            for k in mandatory_consumable_keys:
                self.assertIn(k[0], consumable)
                self.assertIsInstance(consumable[k[0]], k[1])


class CollectivesTests(unittest.TestCase):
    """
    Testing suite for the package :mod:`mate_bot.collectives`
    """

    pass


class CommandsTests(unittest.TestCase):
    """
    Testing suite for the package :mod:`mate_bot.commands`
    """

    pass


class ParsingTests(unittest.TestCase):
    """
    Testing suite for the package :mod:`mate_bot.parsing`
    """

    pass


class StateTests(unittest.TestCase):
    """
    Testing suite for the package :mod:`mate_bot.state`
    """

    pass


if __name__ == "__main__":
    unittest.main()
