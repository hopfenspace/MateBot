"""
MateBot unit tests for helpers and other miscellaneous features
"""

import unittest as _unittest
import random
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

        # Don't allow transactions of unknown users
        with self.assertRaises(ValueError):
            transactions.create_transaction(models.User(), user1, 42, "", self.session, logging.getLogger())

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
        users = self.session.query(models.User).all()
        m, ts = transactions.create_one_to_many_transaction(
            users[0],
            [(users[2], 1), (users[3], 1), (users[4], 1), (users[5], 1)],
            5,
            "foo",
            self.session,
            logging.getLogger(),
            "{reason}{n}"
        )
        self.assertEqual(m.id, 1)
        self.assertEqual(len(ts), 4)
        self.assertEqual(users[0].balance, -62)
        self.assertEqual(users[5].balance, 5)
        for t in ts:
            self.assertEqual(f"foo{t.id}", self.session.query(models.Transaction).get(t.id).reason)
            self.assertEqual(self.session.query(models.Transaction).get(t.id), t)

        m, ts = transactions.create_one_to_many_transaction(
            users[4],
            [(users[2], 4), (users[3], 9), (users[4], 1), (users[5], 2)],
            3,
            "bar",
            self.session,
            logging.getLogger(),
            "{n}_{reason}"
        )
        for i, t in enumerate(ts):
            self.assertEqual(f"{i+1}_bar", self.session.query(models.Transaction).get(t.id).reason)
            self.assertEqual(self.session.query(models.Transaction).get(t.id), t)
        self.assertEqual(self.session.query(models.Transaction).get(4).amount, 5)
        self.assertEqual(self.session.query(models.Transaction).get(5).amount, 12)
        self.assertEqual(self.session.query(models.Transaction).get(6).amount, 27)

    def test_many_to_one_transactions(self):
        pass

    def test_reversed_multi_transactions(self):
        users = self.session.query(models.User).all()
        balances = [u.balance for u in users][:]

        test_cases = [
            (users[4], [(users[1], 1)]),
            (users[1], [(users[4], 2), (users[0], 9)]),
            (users[0], [(users[3], 42), (users[1], 19)]),
            (users[0], [(users[1], 1), (users[2], 5), (users[3], 9), (users[4], 12), (users[5], 38)]),
        ]

        for s, rs in test_cases:
            base_amount = random.randint(1, 42)
            m_from, ts_from = transactions.create_one_to_many_transaction(
                s,
                rs,
                base_amount,
                "foo",
                self.session,
                logging.getLogger()
            )
            m_to, ts_to = transactions.create_many_to_one_transaction(
                rs,
                s,
                base_amount,
                "bar",
                self.session,
                logging.getLogger()
            )

            self.assertEqual(m_from.base_amount, m_to.base_amount)
            self.assertEqual(m_from.base_amount, base_amount)
            self.assertEqual(len(ts_from), len(ts_to))
            self.assertEqual(sum(t.amount for t in ts_from), sum(t.amount for t in ts_to))
            self.assertEqual(balances, [u.balance for u in users])

    def test_matrix_transactions(self):
        pass
