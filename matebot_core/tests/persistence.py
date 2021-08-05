"""
MateBot database unit tests
"""

import datetime
import unittest
from typing import List

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.exc
from sqlalchemy.engine import Engine as _Engine

from .. import schemas
from ..persistence import models


_DATABASE_URL = "sqlite://"


class _BaseDatabaseTests(unittest.TestCase):
    engine: _Engine
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        print("setUp", self)

        self.engine = sqlalchemy.create_engine(
            _DATABASE_URL,
            connect_args={"check_same_thread": False}
        )
        self.session = sqlalchemy.orm.sessionmaker(
            autocommit=False,
            autoflush=False,
            bind=self.engine
        )()
        models.Base.metadata.create_all(bind=self.engine)

    def tearDown(self) -> None:
        self.session.close()
        self.engine.dispose()

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


class DatabaseUsabilityTests(_BaseDatabaseTests):
    """
    Database test cases checking the correct usability of the models
    """

    def test_create_user_without_orm(self):
        self.session.execute(
            sqlalchemy.insert(models.User).values(
                name="name",
                balance=42,
                permission=True,
                external=False
            )
        )
        self.session.commit()

        self.assertEqual(1, len(self.session.query(models.User).all()))
        self.assertTrue(self.session.get(models.User, 1))
        self.assertEqual(self.session.get(models.User, 1).name, "name")
        self.assertEqual(self.session.get(models.User, 1).balance, 42)
        now = int(datetime.datetime.now().timestamp())
        accessed = self.session.get(models.User, 1).accessed.timestamp()
        self.assertLessEqual((now - accessed) % 3600, 1)

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

    def test_create_community_user(self):
        community = self.get_sample_users()[-1]
        self.session.add(community)
        self.session.commit()

        self.assertEqual(community.id, 1)
        self.assertEqual(community.special, True)
        self.assertEqual(community.active, True)

    def test_insert_all_sample_users(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()
        self.assertEqual(len(self.get_sample_users()), len(self.session.query(models.User).all()))


class DatabaseRestrictionTests(_BaseDatabaseTests):
    """
    Database test cases checking restrictions on certain operations (constraints)
    """

    def test_community_user_constraints(self):
        self.session.add_all(self.get_sample_users())
        community = self.get_sample_users()[-1]

        # Non-unique special user flag
        self.session.add(community)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Forbidden special user flag 'false'
        community.special = False
        self.session.add(community)
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

    def test_user_alias_constraints(self):
        # Missing all required fields
        self.session.add(models.UserAlias())
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Everything fine
        self.session.add(models.UserAlias(app_user_id="app-alias1", user_id=1, app_id=1))
        self.session.commit()
        self.session.rollback()

        # Same alias in same application again
        self.session.add(models.UserAlias(app_user_id="app-alias1", user_id=6, app_id=1))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Everything fine
        self.session.add(models.UserAlias(app_user_id="app-alias2", user_id=2, app_id=1))
        self.session.commit()
        self.session.rollback()

        # Same user in same application again
        self.session.add(models.UserAlias(app_user_id="app-alias5", user_id=2, app_id=1))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Everything fine
        self.session.add(models.UserAlias(app_user_id="app-alias2", user_id=2, app_id=6))
        self.session.commit()
        self.session.rollback()

    def test_transaction_constraints(self):
        # Missing all required fields
        self.session.add(models.Transaction())
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Negative amount
        self.session.add(models.Transaction(
            sender_id=1,
            receiver_id=2,
            amount=-32,
            reason="reason",
            transaction_types_id=1
        ))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Zero amount
        self.session.add(models.Transaction(
            sender_id=1,
            receiver_id=2,
            amount=0,
            reason="reason",
            transaction_types_id=1
        ))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Sender equals receiver
        self.session.add(models.Transaction(
            sender_id=1,
            receiver_id=1,
            amount=1,
            reason="reason",
            transaction_types_id=1
        ))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Non-unique transaction ID
        self.session.add(models.Transaction(
            id=1,
            sender_id=1,
            receiver_id=2,
            amount=1,
            transaction_types_id=1
        ))
        self.session.add(models.Transaction(
            id=1,
            sender_id=2,
            receiver_id=1,
            amount=1,
            transaction_types_id=1
        ))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Everything fine here
        self.session.add(models.Transaction(
            sender_id=1,
            receiver_id=2,
            amount=1,
            transaction_types_id=1
        ))
        self.session.commit()
        self.session.rollback()

    def test_vote_constraints(self):
        # Missing required field 'ballot_id'
        self.session.add(models.Vote(user_id=2, vote=0))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Missing required field 'user_id'
        self.session.add(models.Vote(ballot_id=12, vote=-1))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Everything fine
        ballot = models.Ballot(question="Why not?", restricted=True, active=True)
        self.session.add(ballot)
        self.session.commit()

        # Too high 'vote' value
        self.session.add(models.Vote(ballot=ballot, user_id=42, vote=2))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Too low 'vote' value
        self.session.add(models.Vote(ballot=ballot, user_id=42, vote=-2))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Everything fine
        v1 = models.Vote(ballot=ballot, user_id=22, vote=1)
        v2 = models.Vote(ballot=ballot, user_id=6, vote=-1)
        self.session.add_all([v1, v2])
        self.session.commit()

        # Second vote of same user in the same ballot with a different vote
        self.session.add(models.Vote(ballot=ballot, user_id=6, vote=1))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()

        # Second vote of same user in the same ballot with the same vote
        self.session.add(models.Vote(ballot=ballot, user_id=6, vote=-1))
        with self.assertRaises(sqlalchemy.exc.IntegrityError):
            self.session.commit()
        self.session.rollback()


class DatabaseSchemaTests(_BaseDatabaseTests):
    """
    Database test cases checking the usability of schemas together with the models
    """

    def test_create_consumable(self):
        incoming_consumable = schemas.ConsumableCreation(
            name="Cola Mate",
            price=100,
            messages=["Together tastes better", "Taste the feeling", "Open happiness"],
            symbol="\U0001F9C9",
            stock=42
        )

        info = incoming_consumable.dict()
        msgs = info.pop("messages")
        model = models.Consumable(**info)
        self.session.add(model)
        self.session.commit()

        for i, msg in enumerate(msgs):
            msg_model = models.ConsumableMessage(message=msg)
            msg_model.consumable = model
            self.session.add(msg_model)
            self.session.commit()
            self.assertEqual(i+1, msg_model.id)
            self.assertEqual(i+1, len(model.messages))

        for k in incoming_consumable.dict():
            self.assertEqual(getattr(incoming_consumable, k), getattr(model.schema, k))
        self.assertTrue("id" in model.schema.dict())
        self.assertTrue("modified" in model.schema.dict())


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for cls in [DatabaseUsabilityTests, DatabaseRestrictionTests, DatabaseSchemaTests]:
        for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
            suite.addTest(cls(fixture))
    return suite


if __name__ == '__main__':
    unittest.main()
