"""
MateBot core unit tests
"""

import unittest
from .api import APITests
from .load import LoadTests
from .misc import TransactionTests
from .persistence import DatabaseRestrictionTests, DatabaseUsabilityTests


TEST_CLASSES = [
    DatabaseUsabilityTests,
    DatabaseRestrictionTests,
    TransactionTests,
    APITests,
    LoadTests
]


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for cls in TEST_CLASSES:
        for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
            suite.addTest(cls(fixture))
    return suite
