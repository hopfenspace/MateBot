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
