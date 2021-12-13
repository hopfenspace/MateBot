"""
MateBot unit tests for helpers and other miscellaneous features
"""

import unittest as _unittest
import logging
from typing import Type

from matebot_core.persistence import models
from matebot_core.misc import transactions

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

    def test_single_transactions(self):
        user1 = self.session.query(models.User).get(1)
        user4 = self.session.query(models.User).get(4)
        user1_balance = user1.balance
        user4_balance = user4.balance

        # Negative or zero amount is forbidden
        for v in [0, -1, -2, -52, 0.3, 0.9, -1e7]:
            with self.assertRaises(ValueError):
                transactions.create_transaction(user1, user4, v, "", self.session, logging.getLogger())
        self.assertEqual(user1_balance, user1.balance)
        self.assertEqual(user4_balance, user4.balance)

        total = 0
        for i, v in enumerate([3, 41, 51, 9, 3]):
            t = transactions.create_transaction(user4, user1, v, "", self.session, logging.getLogger())
            total += v
            self.assertEqual(t.id, i+1)
            self.assertEqual(t.amount, v)
            self.assertEqual(t.multi_transaction, None)
            self.assertEqual(user1.balance, user1_balance + total)
            self.assertEqual(user4.balance, user4_balance - total)
            self.assertEqual(i+1, len(self.session.query(models.Transaction).all()))

    def test_one_to_many_transactions(self):
        pass

    def test_many_to_one_transactions(self):
        pass

    def test_matrix_transactions(self):
        pass
