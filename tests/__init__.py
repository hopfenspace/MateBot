"""
MateBot core unit tests
"""

import unittest
from . import persistence, schemas


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    suite.addTests(persistence.get_suite())
    suite.addTests(schemas.get_suite())
    return suite
