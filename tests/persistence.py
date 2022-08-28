"""
MateBot database unit tests
"""

import datetime
import unittest as _unittest
from typing import List, Type

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.exc
from sqlalchemy.engine import Engine as _Engine

from matebot_core.api import auth
from matebot_core.persistence import models

from . import conf, utils


persistence_suite = _unittest.TestSuite()


def _tested(cls: Type):
    global persistence_suite
    for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
        persistence_suite.addTest(cls(fixture))
    return cls


class _BaseDatabaseTests(utils.BaseTest):
    engine: _Engine
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        super().setUp()
        opts = {"echo": conf.SQLALCHEMY_ECHOING}
        if self.database_url.startswith("sqlite:"):
            opts = {"connect_args": {"check_same_thread": False}}
        self.engine = sqlalchemy.create_engine(self.database_url, **opts)
        self.session = sqlalchemy.orm.sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )()
        models.Base.metadata.create_all(bind=self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()
        super().tearDown()

    @staticmethod
    def get_sample_users() -> List[models.User]:
        return [
            models.User(name="user1", balance=-42, external=True),
            models.User(name="user2", balance=51, external=False),
            models.User(name="user3", external=True),
            models.User(name="user4", balance=2, external=False),
            models.User(name="user5", permission=False, active=False, external=False, voucher_id=2),
            models.User(external=False),
            models.User(name="community", external=False, special=True, balance=2, permission=True)
        ]


@_tested
class DatabaseUsabilityTests(utils.BasePersistenceTests):
    """
    Database test cases checking the correct usability of the models
    """

    def test_create_user_without_orm(self):
        self.session.execute(
            sqlalchemy.insert(models.User).values(
                name="foo",
                balance=42,
                permission=True,
                external=False
            )
        )
        self.session.commit()

        self.assertEqual(1, len(self.session.query(models.User).all()))
        self.assertTrue(self.session.get(models.User, 1))
        self.assertTrue(hasattr(self.session.get(models.User, 1), "name"))
        self.assertEqual(self.session.get(models.User, 1).balance, 42)
        now = int(datetime.datetime.now().timestamp())
        modified = self.session.get(models.User, 1).modified.timestamp()
        self.assertLessEqual((now - modified) % 3600, 1)

    def test_create_users(self):
        user1, user2, user3, user4, _, _, _ = self.get_sample_users()
        self.session.add_all([user1, user2, user3])
        self.session.commit()
        self.session.add(user4)
        self.session.commit()

        self.assertEqual(4, len(self.session.query(models.User).all()))
        self.assertEqual(self.session.get(models.User, 1), user1)
        self.assertEqual(self.session.get(models.User, 2), user2)
        self.assertEqual(self.session.get(models.User, 3), user3)
        self.assertEqual(self.session.get(models.User, 4), user4)
        self.assertListEqual(self.session.get(models.User, 2).vouching_for, [])
        self.assertListEqual(self.session.get(models.User, 4).vouching_for, [])
        self.assertIsNone(self.session.get(models.User, 5))

        # Check the unique constraint on the user's name
        self.session.add(models.User(name="foo", external=False))
        self.session.commit()
        self.session.add(models.User(name="foo", external=False))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_create_community_user(self):
        community = self.get_sample_users()[-1]
        self.session.add(community)
        self.session.commit()

        self.assertEqual(community.id, 1)
        self.assertEqual(community.special, True)
        self.assertEqual(community.active, True)

    def test_insert_and_delete_all_sample_users(self):
        self.assertEqual([], self.session.query(models.User).filter_by(special=True).all())

        self.session.add_all(self.get_sample_users())
        self.session.commit()
        self.assertEqual(len(self.get_sample_users()), len(self.session.query(models.User).all()))
        self.assertEqual(
            [self.session.get(models.User, len(self.get_sample_users()))],
            self.session.query(models.User).filter_by(special=True).all()
        )

        self.session.query(models.User).filter_by(external=True).delete()
        self.session.commit()
        self.assertEqual(len(self.get_sample_users())-2, len(self.session.query(models.User).all()))

        if self.database_type == utils.DatabaseType.SQLITE:
            self.session.query(models.User).delete()
            self.session.commit()
            self.assertEqual(0, len(self.session.query(models.User).all()))
        else:
            with self.assertRaises(sqlalchemy.exc.IntegrityError):
                self.session.query(models.User).delete()
                self.session.commit()

    def test_create_aliases_and_delete_on_cascade(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()
        self.assertEqual(len(self.get_sample_users()), len(self.session.query(models.User).all()))

        app1 = models.Application(name="app1", password=auth.hash_password("password1", "salt"), salt="salt")
        app2 = models.Application(name="app2", password=auth.hash_password("password2", "salt"), salt="salt")
        self.session.add_all([app1, app2])
        self.session.commit()

        user1 = self.session.query(models.User).get(3)
        user2 = self.session.query(models.User).get(5)
        alias1 = models.Alias(username="alias1", application_id=app1.id, user_id=3, confirmed=True)
        alias2 = models.Alias(username="alias2", application_id=app2.id)
        alias2.user = user2

        self.session.add_all([alias1, alias2])
        self.session.commit()
        self.assertFalse(alias2.confirmed)
        self.assertEqual(2, len(self.session.query(models.Alias).all()))

        self.session.delete(user1)
        self.session.commit()
        self.assertIsNone(self.session.query(models.Alias).get(alias1.id))
        self.assertEqual(1, len(self.session.query(models.Alias).all()))

        self.session.delete(user2)
        self.session.commit()
        self.assertIsNone(self.session.query(models.Alias).get(alias2.id))
        self.assertEqual(0, len(self.session.query(models.Alias).all()))

    def test_add_applications_and_aliases(self):
        app1 = models.Application(name="app1", password=auth.hash_password("password1", "salt"), salt="salt")
        app2 = models.Application(name="app2", password=auth.hash_password("password2", "salt"), salt="salt")
        self.session.add_all([app1, app2])
        self.session.commit()

        self.assertEqual("app1", app1.name)
        self.assertEqual("app2", app2.name)

        community_user = self.get_sample_users()[-1]
        self.session.add(community_user)
        self.session.commit()

    def test_applications_and_callbacks(self):
        app1 = models.Application(name="app1", password=auth.hash_password("password1", "salt"), salt="salt")
        self.session.add(app1)
        self.session.commit()

        self.assertTrue(isinstance(app1.callbacks, list))
        self.assertEqual([], app1.callbacks)

        callback = models.Callback(url="http://example.com", application_id=app1.id)
        self.session.add(callback)
        self.session.commit()

        self.assertTrue(isinstance(app1.callbacks, list))
        self.assertEqual(1, len(app1.callbacks))
        self.assertEqual(callback, app1.callbacks[0])

        self.session.delete(callback)
        self.session.commit()

        self.assertTrue(isinstance(app1.callbacks, list))
        self.assertEqual([], app1.callbacks)

        app2 = models.Application(name="app2", password=auth.hash_password("password2", "salt"), salt="salt")
        self.session.add(app2)
        self.session.commit()

        callback = models.Callback(url="http://example.net", application_id=app2.id)
        self.session.add(callback)
        self.session.commit()

        self.session.delete(app2)
        self.session.commit()

        self.assertEqual(0, len(self.session.query(models.Callback).all()))

    def test_communisms(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()

        # Adding a communism
        communism = models.Communism(amount=42, creator_id=1, description="")
        self.session.add(communism)
        self.session.commit()
        self.assertIsNotNone(communism.creator)
        self.assertIs(communism, self.session.query(models.Communism).first())

        # Adding communism participants
        self.session.add_all([
            models.CommunismUsers(communism_id=communism.id, user_id=1, quantity=1),
            models.CommunismUsers(communism_id=communism.id, user_id=2, quantity=2),
            models.CommunismUsers(communism_id=communism.id, user_id=3, quantity=3)
        ])
        self.session.commit()
        self.assertEqual(6, sum([u.quantity for u in communism.participants]))
        self.assertEqual(3, len(self.session.query(models.CommunismUsers).all()))

        # Adding yet another communism participant
        new_participant = models.CommunismUsers(user_id=4, quantity=4)
        communism.participants.append(new_participant)
        self.session.commit()
        self.assertEqual(10, sum([u.quantity for u in communism.participants]))
        self.assertEqual(4, len(self.session.query(models.CommunismUsers).all()))
        self.assertEqual(4, len(self.session.query(models.Communism).get(1).participants))
        self.assertEqual(4, new_participant.id)
        self.assertIs(new_participant.user, self.session.query(models.User).get(4))

        # Participant without communism
        self.session.add(models.CommunismUsers(communism_id=22, user_id=3, quantity=3))
        try:
            self.session.commit()
            self.assertEqual(5, len(self.session.query(models.CommunismUsers).all()))
        except sqlalchemy.exc.DatabaseError:
            if self.database_type != utils.DatabaseType.MYSQL:
                raise
            self.session.rollback()
        self.assertEqual(4, len(self.session.query(models.Communism).get(1).participants))

        # Deleting a communism
        self.session.delete(communism)
        self.session.commit()
        if self.database_type != utils.DatabaseType.MYSQL:
            self.assertEqual(1, len(self.session.query(models.CommunismUsers).all()))
        else:
            self.assertEqual(0, len(self.session.query(models.CommunismUsers).all()))
        self.assertIsNone(self.session.query(models.Communism).get(1))
        self.assertListEqual([], self.session.query(models.Communism).all())

        # Ensure that some error happens when accessing a deleted instance
        try:
            self.assertIsNotNone(repr(communism.participants))
            self.fail()
        except sqlalchemy.orm.exc.DetachedInstanceError as exc:
            self.assertTrue(exc)

        # Ensure that adding an already deleted instance is not possible
        try:
            self.session.add(communism)
            self.session.commit()
            self.fail()
        except sqlalchemy.exc.InvalidRequestError as exc:
            self.assertTrue(exc)
            self.session.rollback()

        # Create a new communism which replaces the old one's ID on sqlite database backend
        new_communism = models.Communism(
            active=False,
            amount=6,
            description="new communism",
            creator_id=5
        )
        self.session.add(new_communism)
        self.session.commit()
        if self.database_type == utils.DatabaseType.SQLITE:
            self.assertEqual(1, new_communism.id)
        else:
            self.assertEqual(2, new_communism.id)
        self.assertIsNotNone(new_communism.creator)

        if self.database_type == utils.DatabaseType.SQLITE:
            new_communism.creator_id = 42
            self.session.commit()
            self.assertIsNone(new_communism.creator)

    def test_ballots(self):
        ballot = models.Ballot()
        self.session.add(ballot)
        self.session.commit()
        self.assertEqual(ballot.result, 0)

        self.session.add_all(self.get_sample_users())
        self.session.commit()

        self.session.add(models.Vote(vote=False, user_id=1, ballot=ballot))
        self.session.commit()
        self.assertEqual(ballot.result, -1)

        self.session.add(models.Vote(vote=False, user_id=2, ballot=ballot))
        self.session.commit()
        self.assertEqual(ballot.result, -2)

        self.session.add(models.Vote(vote=True, user_id=3, ballot=ballot))
        self.session.commit()
        self.assertEqual(ballot.result, -1)

        self.session.add(models.Vote(vote=True, user_id=4, ballot=ballot))
        self.session.commit()
        self.assertEqual(ballot.result, 0)

        self.session.add(models.Vote(vote=True, user_id=5, ballot=ballot))
        self.session.commit()
        self.assertEqual(ballot.result, 1)

        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.add(models.Vote(vote=True, user_id=5, ballot=ballot))
            self.session.commit()
        self.session.rollback()
        self.assertEqual(ballot.result, 1)

        ballot = models.Ballot()
        self.session.add(ballot)
        self.session.commit()
        self.assertEqual(ballot.result, 0)

    def test_multi_transactions(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()

        # Three people donate their money to one
        m1 = models.MultiTransaction(base_amount=4)
        self.session.add(m1)
        self.session.commit()
        self.session.add_all([
            models.Transaction(sender_id=2, receiver_id=1, amount=4, multi_transaction_id=1),
            models.Transaction(sender_id=3, receiver_id=1, amount=4, multi_transaction_id=1),
            models.Transaction(sender_id=4, receiver_id=1, amount=4, multi_transaction_id=1)
        ])
        self.session.commit()
        self.assertEqual(m1.base_amount, 4)
        self.assertEqual(m1.schema.total_amount, 12)

        # Four people get paid by one equally
        m2 = models.MultiTransaction(base_amount=3)
        self.session.add(m2)
        self.session.commit()
        self.session.add_all([
            models.Transaction(sender_id=2, receiver_id=1, amount=2, multi_transaction_id=2),
            models.Transaction(sender_id=2, receiver_id=3, amount=2, multi_transaction_id=2),
            models.Transaction(sender_id=2, receiver_id=5, amount=2, multi_transaction_id=2),
            models.Transaction(sender_id=2, receiver_id=6, amount=2, multi_transaction_id=2)
        ])
        self.session.commit()
        self.assertEqual(m2.schema.total_amount, 8)

        # Six people pay to two guys unequally (6th person payer pays twice)
        self.session.add(models.User(name="foo", balance=-132, external=False))
        self.session.add(models.User(name="bar", balance=3, external=False))
        m3 = models.MultiTransaction(base_amount=10)
        self.session.add(m3)
        self.session.commit()
        self.session.add_all([
            models.Transaction(sender_id=1, receiver_id=8, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=1, receiver_id=9, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=2, receiver_id=8, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=2, receiver_id=9, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=3, receiver_id=8, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=3, receiver_id=9, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=4, receiver_id=8, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=4, receiver_id=9, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=5, receiver_id=8, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=5, receiver_id=9, amount=10, multi_transaction_id=3),
            models.Transaction(sender_id=6, receiver_id=8, amount=20, multi_transaction_id=3),
            models.Transaction(sender_id=6, receiver_id=9, amount=20, multi_transaction_id=3)
        ])
        self.session.commit()
        self.assertEqual(len(m3.transactions), 12)
        self.assertEqual(m3.schema.total_amount, 140)


@_tested
class DatabaseRestrictionTests(utils.BasePersistenceTests):
    """
    Database test cases checking restrictions on certain operations (constraints)
    """

    def test_community_user_constraints(self):
        self.session.add(models.User(external=False, special=False, permission=False))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        self.session.add_all(self.get_sample_users())
        community = self.get_sample_users()[-1]

        # Non-unique special user flag
        self.session.add(community)
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Forbidden special user flag 'false'
        community = self.get_sample_users()[-1]
        community.special = False
        self.session.add(community)
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

    def test_user_alias_constraints(self):
        self.assertEqual(0, len(self.session.query(models.Application).all()))

        # Missing all required fields
        self.session.add(models.Alias())
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Missing user, if foreign key constraints are enforced
        self.session.add(models.Alias(username="app-alias1", user_id=1, application_id=1))
        try:
            self.session.commit()
        except sqlalchemy.exc.DatabaseError:
            if self.database_type != utils.DatabaseType.MYSQL:
                raise
            self.session.rollback()

        # Creating users to fix the aforementioned problem
        self.session.add_all(self.get_sample_users())
        self.session.commit()

        # Missing application, if foreign key constraints are enforced
        if self.database_type != utils.DatabaseType.SQLITE:
            with self.assertRaises(sqlalchemy.exc.IntegrityError):
                self.session.add(models.Alias(username="app-alias2", user_id=2, application_id=1))
                self.session.commit()
            self.session.rollback()

        # Creating an application
        self.session.add(models.Application(name="app", password="password", salt="salt"))
        self.session.commit()

        # Now, the alias can be created
        self.session.add(models.Alias(username="app-alias2", user_id=2, application_id=1))
        self.session.commit()

        # Same alias in same application again
        self.session.add(models.Alias(username="app-alias2", user_id=2, application_id=1))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()
        self.session.add(models.Alias(username="app-alias2", user_id=3, application_id=1))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

    def test_transaction_constraints(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()

        # Missing all required fields
        self.session.add(models.Transaction())
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Negative amount
        self.session.add(models.Transaction(
            sender_id=1,
            receiver_id=2,
            amount=-32,
            reason="reason"
        ))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Zero amount
        self.session.add(models.Transaction(
            sender_id=1,
            receiver_id=2,
            amount=0,
            reason="reason"
        ))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Sender equals receiver
        self.session.add(models.Transaction(
            sender_id=1,
            receiver_id=1,
            amount=1,
            reason="reason"
        ))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Non-unique transaction ID
        self.session.add(models.Transaction(
            id=1,
            sender_id=1,
            receiver_id=2,
            amount=1
        ))
        self.session.add(models.Transaction(
            id=1,
            sender_id=2,
            receiver_id=1,
            amount=1
        ))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

    def test_vote_constraints(self):
        # Missing required field 'ballot_id'
        self.session.add(models.Vote(user_id=2, vote=True))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Missing required field 'user_id'
        self.session.add(models.Vote(ballot_id=12, vote=False))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Intermediate ballot required
        self.session.add(models.Refund(description="Why not?", active=True, amount=3, creator_id=1))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()
        self.session.add(models.Ballot())
        self.session.commit()

        # Rejecting refunds with non-existing creator
        if self.database_type != utils.DatabaseType.SQLITE:
            self.session.add(models.Refund(description="Why not?", active=True, amount=3, creator_id=1, ballot_id=1))
            with self.assertRaises(sqlalchemy.exc.DatabaseError):
                self.session.commit()
            self.session.rollback()

        # Creating the user to fix the aforementioned error
        self.session.add(models.User(name="foo", external=False, permission=True))
        self.session.commit()

        # Everything fine now
        refund = models.Refund(description="Why not?", active=True, amount=3, creator_id=1, ballot_id=1)
        self.session.add(refund)
        self.session.commit()

        # Invalid 'vote' value
        self.session.add(models.Vote(ballot_id=1, user_id=42, vote=1337))
        with self.assertRaises(sqlalchemy.exc.StatementError):
            self.session.commit()
        self.session.rollback()

        # Failing foreign key constraint due to unknown user
        if self.database_type == utils.DatabaseType.MYSQL:
            with self.assertRaises(sqlalchemy.exc.DatabaseError):
                self.session.add(models.Vote(ballot=refund.ballot, user_id=42, vote=True))
                self.session.commit()
            self.session.rollback()

        # Everything fine
        self.session.add_all(self.get_sample_users())
        self.session.commit()
        v1 = models.Vote(ballot_id=1, user_id=2, vote=True)
        v2 = models.Vote(ballot=refund.ballot, user_id=4, vote=False)
        self.session.add_all([v1, v2])
        self.session.commit()

        # Second vote of same user in the same ballot with a different vote
        self.session.add(models.Vote(ballot=refund.ballot, user_id=4, vote=True))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        # Second vote of same user in the same ballot with the same vote
        self.session.add(models.Vote(ballot=refund.ballot, user_id=4, vote=False))
        with self.assertRaises(sqlalchemy.exc.DatabaseError):
            self.session.commit()
        self.session.rollback()

        self.assertEqual(0, refund.ballot.result)


if __name__ == '__main__':
    _unittest.main()
