"""
MateBot testing suite
"""

import sys
import typing
import unittest
import functools


DEFAULT_WEIGHT = 0


def significance(
        weight_or_fn: typing.Union[typing.Callable, int],
        optional_weight: typing.Optional[int] = None
) -> typing.Callable:
    """
    Wrap around a callable to add a property ``significance`` to it

    This property can be used to sort and compare different functions or methods
    based on their "weight". A higher weight should be executed earlier, a lower
    weight later. This feature is used to sort different test cases.

    .. note::
        Note that you can only sort functions and methods of a class using this
        feature, not the class itself. The sorting of the test cases takes place
        in the method :meth:`SortedTestSuite.sort`. Look into its docs for more details.

    The following valid example illustrates how the wrapper can be used on a function:

        >>> from test import significance, DEFAULT_WEIGHT
        >>> @significance
        ... def f():
        ...     pass
        ...
        >>> @significance(42)
        ... def g():
        ...     pass
        ...
        >>> f.significance == DEFAULT_WEIGHT
        True
        >>> g.significance
        42
        >>>

    :param weight_or_fn: either function that should be wrapped or integer that reflects the
        significance / importance of the function that should be wrapped up
    :type weight_or_fn: typing.Union[typing.Callable, int]
    :param optional_weight: optional weight of the function or feature that has been wrapped up
    :type optional_weight: typing.Optional[int]
    :return: wrapped function that provides a property ``significance`` now
    :rtype: typing.Callable
    :raises TypeError: when the first argument is not integer nor callable
    :raises ValueError: when the first argument is an integer and the second not ``None``
    """

    if isinstance(weight_or_fn, int):
        weight = weight_or_fn

        if optional_weight is not None:
            raise ValueError(f"Second parameter should be None, not {type(optional_weight)}")

        def wrap_outer(fn: typing.Callable) -> typing.Callable:
            setattr(fn, "significance", weight)

            @functools.wraps(fn)
            def wrap_inner(*args, **kwargs):
                return fn(*args, **kwargs)

            return wrap_inner

        return wrap_outer

    elif isinstance(weight_or_fn, typing.Callable):
        func = weight_or_fn
        weight = optional_weight
        if optional_weight is None:
            weight = DEFAULT_WEIGHT

        @functools.wraps(func)
        def wrap(*args, **kwargs):
            return func(*args, **kwargs)

        setattr(wrap, "significance", weight)
        return wrap

    else:
        raise TypeError(f"Expected callable or int as first argument, not {type(weight_or_fn)})")


class SortedTestSuite(unittest.TestSuite):
    """
    Test suite as collection of a number of TestCases that can be sorted by significance

    For more information, see the base class :class:`unittest.suite.TestSuite`.
    """

    def sort(self) -> None:
        """
        Sort the test cases and test suites based on their significance in-place

        This method should be executed directly before :meth:`run` starts.
        It sorts the assigned test cases by their significance in-place.

        :return: None
        """

        def calc_test_case(case: unittest.TestCase) -> int:
            if hasattr(case, "significance"):
                return -case.significance
            if not hasattr(case, "_testMethodName"):
                raise TypeError("Expected TestCase instance with attribute _testMethodName")

            method = getattr(case, case._testMethodName, None)
            if method is not None and hasattr(method, "significance"):
                return -method.significance
            return DEFAULT_WEIGHT

        def significance_sorting(value: typing.Union[SortedTestSuite, unittest.TestCase]) -> int:
            if isinstance(value, SortedTestSuite):
                if hasattr(value, "significance"):
                    return -value.significance

                total = 0
                for test in value.get():
                    total += calc_test_case(test)

                return -total or DEFAULT_WEIGHT

            elif isinstance(value, unittest.TestCase):
                return calc_test_case(value)

            else:
                raise TypeError(f"Expected SortedTestSuite or a TestCase object, not {type(value)}")

        self._tests.sort(key=significance_sorting)

    def get(self) -> typing.List[unittest.TestCase]:
        """
        Retrieve the list of test cases that are currently assigned to this test suite

        :return: list of assigned test case instances
        :rtype: typing.List[unittest.TestCase]
        """

        return self._tests

    def run(self, result: unittest.TestResult, debug: bool = False) -> unittest.TestResult:
        """
        Run the test suite

        See the documentation of the ``unittest`` package for more information,
        see `here <https://docs.python.org/3/library/unittest.html>`_.
        """

        self.sort()
        return super().run(result)


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

    def test_significance(self):
        @significance
        def f():
            pass

        @significance(42)
        def g():
            pass

        self.assertEqual(f.significance, DEFAULT_WEIGHT)
        self.assertEqual(g.significance, 42)


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

    def setUp(self):
        from mate_bot.config import config
        from mate_bot.state.dbhelper import BackendHelper

        if "testing" not in config:
            raise unittest.SkipTest("no testing database settings")

        self.helper = BackendHelper
        settings = config["database"].copy()
        settings.update(config["testing"].copy())
        self.helper.db_config = settings
        self.helper.query_logger = logging.getLogger("database")

    def tearDown(self):
        from mate_bot.config import config
        self.helper.db_config = config["database"].copy()


    def test_db_schema_conversion(self):
        from mate_bot.state.dbhelper import DATABASE_SCHEMA as SCHEMA

        mandatory_keys = [
            "users",
            "transactions",
            "collectives",
            "collectives_users",
            "collective_messages",
            "externals"
        ]

        for k in mandatory_keys:
            self.assertIn(k, SCHEMA)

        self.assertEqual(str(SCHEMA["users"]), SCHEMA["users"]._to_string(4))

        self.assertEqual(
            SCHEMA["users"]._to_string(0),
            "CREATE TABLE users ("
            "`id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT, "
            "`tid` BIGINT UNIQUE, "
            "`username` VARCHAR(255), "
            "`name` VARCHAR(255) NOT NULL, "
            "`balance` MEDIUMINT NOT NULL DEFAULT 0, "
            "`permission` BOOLEAN NOT NULL DEFAULT false, "
            "`active` BOOLEAN NOT NULL DEFAULT true, "
            "`created` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP, "
            "`accessed` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP);"
        )

        self.assertEqual(
            SCHEMA["externals"]._to_string(0),
            "CREATE TABLE externals ("
            "`id` INT NOT NULL PRIMARY KEY AUTO_INCREMENT, "
            "`internal` INT, "
            "`external` INT NOT NULL UNIQUE, "
            "`changed` TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP, "
            "FOREIGN KEY (internal) REFERENCES users(id) ON DELETE CASCADE, "
            "FOREIGN KEY (external) REFERENCES users(id) ON DELETE CASCADE);"
        )

    def test_db_execute(self):
        pass

    def test_db_checking(self):
        pass

    def test_db_rebuild_database(self):
        pass

    def test_db_get_values_by_key_manually(self):
        pass

    def test_db_get_values_by_key(self):
        pass

    def test_db_get_value_manually(self):
        pass

    def test_db_get_value(self):
        pass

    def test_db_set_value_manually(self):
        pass

    def test_db_set_value(self):
        pass

    def test_db_set_all_manually(self):
        pass

    def test_db_set_all(self):
        pass

    def test_db_insert_manually(self):
        pass

    def test_db_insert(self):
        pass

    def test_db_extract_all(self):
        pass


if __name__ == "__main__":
    loader = unittest.loader.TestLoader()
    loader.suiteClass = SortedTestSuite
    unittest.main(testLoader=loader)
