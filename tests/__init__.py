"""
MateBot core unit tests
"""

import unittest
from . import api, persistence
from .api import WorkingAPITests, FailingAPITests
from .persistence import DatabaseUsabilityTests, DatabaseRestrictionTests, DatabaseSchemaTests


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    suite.addTests(api.get_suite())
    suite.addTests(persistence.get_suite())
    return suite
