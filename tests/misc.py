"""
MateBot unit tests for helpers and other miscellaneous features
"""

import unittest as _unittest
from typing import Type

from . import utils


misc_suite = _unittest.TestSuite()


def _tested(cls: Type):
    global misc_suite
    for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
        misc_suite.addTest(cls(fixture))
    return cls


@_tested
class TransactionTests(utils.BasePersistenceTests):
    def setUp(self) -> None:
        super().setUp()
        self.session.add_all(self.get_sample_users())
        self.session.commit()

    def test_restrictions_single(self):
        pass

    def test_creation_single(self):
        pass

    def test_restrictions_one_to_many(self):
        pass

    def test_creation_one_to_many(self):
        pass

    def test_restrictions_many_to_one(self):
        pass

    def test_creation_many_to_one(self):
        pass

    def test_restrictions_matrix(self):
        pass

    def test_creation_matrix(self):
        pass
