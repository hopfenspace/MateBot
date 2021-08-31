"""
MateBot core unit tests
"""

import unittest
from .api import *
from .persistence import *


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    suite.addTests(api_suite)
    suite.addTests(persistence_suite)
    return suite
