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

    def test_simple_multi_transaction_restrictions(self):
        users = self.session.query(models.User).all()

        for func, direction, total in [
            (transactions.create_one_to_many_transaction_by_base, True, False),
            (transactions.create_many_to_one_transaction_by_base, False, False),
            (transactions.create_one_to_many_transaction_by_total, True, True),
            (transactions.create_many_to_one_transaction_by_total, False, True),
        ]:
            if direction:
                def f(one, many, amount):
                    return func(one, many, amount, "foo", self.session, logging.getLogger())
            else:
                def f(one, many, amount):
                    return func(many, one, amount, "foo", self.session, logging.getLogger())

            # At least one valid user with quantity > 1 must be present
            with self.assertRaises(ValueError, msg=func):
                f(users[1], [], 1337)
            if total:
                with self.assertRaises(ValueError, msg=func):
                    f(users[4], [(users[4], 1)], 1337)
                with self.assertRaises(ValueError, msg=func):
                    f(users[4], [(users[4], 1), (users[4], 1), (users[4], 1)], 1337)

            # Quantities mustn't be negative
            with self.assertRaises(ValueError, msg=func):
                f(users[1], [(users[4], -1)], 1337)
            with self.assertRaises(ValueError, msg=func):
                f(users[1], [(users[4], 6), (users[4], -2)], 1337)

            # Specifying the same receivers multiple times just yields one transaction to them
            m, ts = f(users[1], [(users[4], 1), (users[4], 1), (users[4], 1)], 1337)
            self.assertEqual(1, len(ts))
            self.assertEqual(m.transactions, ts)
            self.assertGreaterEqual(ts[0].amount, 1337)

            # The amount must not be negative or zero
            for v in [0, 0.2, 0.9, -42, -1e10, -0.1, -random.randint(2, 1024)]:
                with self.assertRaises(ValueError, msg=func):
                    f(users[1], [(users[4], 2)], v)

    def test_simple_multi_transaction_base(self):
        users = self.session.query(models.User).all()
        ms = 0

        for switch in (0, 1):
            if switch:
                def f(a, b, amount, **kwargs):
                    return transactions.create_one_to_many_transaction_by_base(
                        a, b, amount, "foo", self.session, logging.getLogger(), **kwargs
                    )
            else:
                def f(a, b, amount, **kwargs):
                    return transactions.create_many_to_one_transaction_by_base(
                        b, a, amount, "foo", self.session, logging.getLogger(), **kwargs
                    )

            # Base amount, total amount, (ID, change) of the one, list of (ID, quantity, change) of the many
            test_cases = [
                (7, 70, (0, 70), [(1, 1, 7), (2, 2, 14), (3, 3, 21), (4, 4, 28)]),
                (5, 35, (1, 35), [(0, 1, 15), (0, 1, 15), (0, 1, 15), (2, 3, 15), (3, 1, 5)]),
                (2, 18, (4, 18), [(0, 4, 8), (1, 4, 8), (2, 1, 2)]),
                (10, 100, (0, 100), [(1, 1, 10), (2, 2, 20), (3, 3, 30), (4, 4, 40)]),
                (99, 99, (4, 99), [(1, 1, 99)]),
                (23, 253, (2, 253), [(1, 1, 23), (3, 9, 207), (4, 1, 23)])
            ]

            for test in test_cases:
                base, total, (one, one_c), many = test
                quantified_many = [(users[uid], q) for uid, q, _ in many]
                balances = [u.balance for u in users][:]

                m, ts = f(users[one], quantified_many, base)
                ms += 1
                self.assertEqual(m.id, ms)
                self.assertEqual(m.base_amount, base)
                self.assertEqual(sum(t.amount for t in m.transactions), sum(t.amount for t in ts))
                self.assertEqual(sum(t.amount for t in ts), total)

                if switch:
                    self.assertEqual(users[one].balance, balances[one] - one_c)
                    for user_id, _, change in many:
                        self.assertEqual(users[user_id].balance, balances[user_id] + change)
                else:
                    self.assertEqual(users[one].balance, balances[one] + one_c)
                    for user_id, _, change in many:
                        self.assertEqual(users[user_id].balance, balances[user_id] - change)

    def test_one_to_many_transactions_base(self):
        users = self.session.query(models.User).all()

        # First basic check of equal parts for everyone
        m, ts = transactions.create_one_to_many_transaction_by_base(
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

        # Quantities should be handled correctly
        m, ts = transactions.create_one_to_many_transaction_by_base(
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

        # Users can't send money to themselves
        m, ts = transactions.create_one_to_many_transaction_by_base(
            users[1],
            [(users[1], 1)],
            4,
            "foo",
            self.session,
            logging.getLogger()
        )
        self.assertEqual(0, len(ts))
        self.assertEqual(0, len(m.transactions))

        # Users can't send money to themselves, no matter how often they try
        m, ts = transactions.create_one_to_many_transaction_by_base(
            users[1],
            [(users[1], 2), (users[1], 6), (users[1], 0), (users[1], 1337)],
            4,
            "foo",
            self.session,
            logging.getLogger()
        )
        self.assertEqual(0, len(ts))
        self.assertEqual(0, len(m.transactions))

    def test_one_to_many_transactions_total(self):
        users = self.session.query(models.User).all()

        # Starting with a base case
        balance_user1 = users[1].balance
        balance_user2 = users[2].balance
        balance_user3 = users[3].balance
        balance_user4 = users[4].balance
        m, ts = transactions.create_one_to_many_transaction_by_total(
            users[0],
            [(users[1], 7), (users[2], 0), (users[3], 9), (users[4], 2)],
            215,
            "foo",
            self.session,
            logging.getLogger()
        )
        self.assertEqual(m.base_amount, 12)
        self.assertEqual(sum(t.amount for t in m.transactions), sum(t.amount for t in ts))
        self.assertGreaterEqual(sum(t.amount for t in ts), 215)
        self.assertEqual(users[1].balance, balance_user1 + 7 * 12)
        self.assertEqual(users[2].balance, balance_user2 + 0 * 12)
        self.assertEqual(users[3].balance, balance_user3 + 9 * 12)
        self.assertEqual(users[4].balance, balance_user4 + 2 * 12)

        # Adding more complex test scenarios
        test_cases = [
            (25, 25, users[4], [(1, 1, 25)]),
            (91, 31, users[4], [(1, 1, 93), (1, 1, 93), (1, 1, 93)]),
            (734, 67, users[1], [(4, 2, 134), (0, 9, 603)]),
            (623, 11, users[0], [(3, 42, 462), (1, 19, 209)]),
            (9814, 151, users[0], [(1, 1, 151), (2, 5, 755), (3, 9, 1359), (4, 12, 1812), (5, 38, 5738)])
        ]

        # Transactions by total amount must be "fair" (=equally distributed) in various situations
        for total, base, s, rs_a in test_cases:
            rs = [(users[r_id], q) for r_id, q, _ in rs_a]
            balances = [u.balance for u in users][:]
            m, ts = transactions.create_one_to_many_transaction_by_total(
                s,
                rs,
                total,
                "foo",
                self.session,
                logging.getLogger()
            )
            self.assertEqual(m.base_amount, base)
            self.assertEqual(sum(t.amount for t in m.transactions), sum(t.amount for t in ts))
            self.assertGreaterEqual(sum(t.amount for t in ts), total)
            for user_id, _, increase in rs_a:
                self.assertEqual(users[user_id].balance, balances[user_id] + increase)

    def test_many_to_one_transactions_total(self):
        users = self.session.query(models.User).all()

        test_cases = [
            (42, 42, users[1], [(3, 1, 42)]),
            (1337, 1337, users[2], [(2, 1, -1337), (1, 1, 1337)]),
            (8351, 182, users[0], [(1, 6, 1092), (2, 9, 1638), (3, 31, 5642), (4, 0, 0)]),
            (9999, 3333, users[1], [(2, 1, 3333), (3, 1, 3333), (4, 1, 3333)]),
            (10000, 3334, users[1], [(2, 1, 3334), (3, 1, 3334), (4, 1, 3334)]),
            (17693, 770, users[3], [(0, 7, 5390), (1, 8, 6160), (2, 8, 6160)])
        ]

        for total, base, r, ss_a in test_cases:
            ss = [(users[s_id], q) for s_id, q, _ in ss_a]
            balances = [u.balance for u in users][:]
            m, ts = transactions.create_many_to_one_transaction_by_total(
                ss,
                r,
                total,
                "foo",
                self.session,
                logging.getLogger()
            )
            self.assertEqual(m.base_amount, base)
            self.assertEqual(sum(t.amount for t in m.transactions), sum(t.amount for t in ts))
            self.assertGreaterEqual(sum(t.amount for t in ts), total)
            for user_id, _, decrease in ss_a:
                self.assertEqual(users[user_id].balance, balances[user_id] - decrease)

    def test_reversed_multi_transactions(self):
        users = self.session.query(models.User).all()
        balances = [u.balance for u in users][:]

        test_cases = [
            (users[4], [(users[1], 1)]),
            (users[4], [(users[4], 1)]),
            (users[4], [(users[1], 1), (users[1], 1), (users[1], 1)]),
            (users[1], [(users[4], 2), (users[0], 9)]),
            (users[0], [(users[3], 42), (users[1], 19)]),
            (users[0], [(users[1], 1), (users[2], 5), (users[3], 9), (users[4], 12), (users[5], 38)])
        ]

        for s, rs in test_cases:
            base_amount = random.randint(1, 42)
            m_from, ts_from = transactions.create_one_to_many_transaction_by_base(
                s,
                rs,
                base_amount,
                "foo",
                self.session,
                logging.getLogger()
            )
            m_to, ts_to = transactions.create_many_to_one_transaction_by_base(
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

        self.assertEqual(12, len(self.session.query(models.MultiTransaction).all()))
        self.assertEqual(22, len(self.session.query(models.Transaction).all()))

    def test_matrix_transactions(self):
        pass
