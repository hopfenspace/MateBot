"""
MateBot core unit tests
"""

import unittest
from . import api, persistence
from .api import suite as api_suite
from .persistence import suite as persistence_suite


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    suite.addTests(api_suite)
    suite.addTests(persistence_suite)
    return suite
