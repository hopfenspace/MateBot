"""
MateBot database unit tests
"""

import datetime
import unittest
from typing import Callable, List

import sqlalchemy
import sqlalchemy.orm
import sqlalchemy.exc
from sqlalchemy.engine import Engine as _Engine

from matebot_core import schemas
from matebot_core.persistence import models

from . import database


class _BaseDatabaseTests(unittest.TestCase):
    database_url: str
    cleanup_database: Callable[[], None]
    engine: _Engine
    session: sqlalchemy.orm.Session

    def setUp(self) -> None:
        self.database_url, self.cleanup_database = database.get_database_url()
        opts = {}
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
        self.cleanup_database()

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

    def test_insert_and_delete_all_sample_users(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()
        self.assertEqual(len(self.get_sample_users()), len(self.session.query(models.User).all()))

        self.session.query(models.User).delete()
        self.session.commit()
        self.assertEqual(0, len(self.session.query(models.User).all()))

    def test_create_aliases_and_delete_on_cascade(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()
        self.assertEqual(len(self.get_sample_users()), len(self.session.query(models.User).all()))

        app1 = models.Application(name="app1")
        app2 = models.Application(name="app2")
        self.session.add_all([app1, app2])
        self.session.commit()

        user1 = self.session.query(models.User).get(3)
        user2 = self.session.query(models.User).get(5)
        alias1 = models.UserAlias(app_user_id="alias1", app_id=app1.id, user_id=3)
        alias2 = models.UserAlias(app_user_id="alias2", app_id=app2.id)
        alias2.user = user2

        self.session.add_all([alias1, alias2])
        self.session.commit()
        self.assertEqual(2, len(self.session.query(models.UserAlias).all()))

        self.session.delete(user1)
        self.session.commit()
        self.assertIsNone(self.session.query(models.UserAlias).get(alias1.id))
        self.assertEqual(1, len(self.session.query(models.UserAlias).all()))

        self.session.delete(user2)
        self.session.commit()
        self.assertIsNone(self.session.query(models.UserAlias).get(alias2.id))
        self.assertEqual(0, len(self.session.query(models.UserAlias).all()))

    def test_add_applications_and_aliases(self):
        app1 = models.Application(name="app1")
        app2 = models.Application(name="app2")
        self.session.add_all([app1, app2])
        self.session.commit()

        self.assertEqual("app1", app1.name)
        self.assertEqual("app2", app2.name)

        community_user = self.get_sample_users()[-1]
        self.session.add(community_user)
        self.session.commit()

        community_alias1 = models.UserAlias(
            app_id=app1.id,
            user_id=community_user.id,
            app_user_id="community_alias1"
        )
        community_alias2 = models.UserAlias(
            app_id=app2.id,
            app_user_id="community_alias2"
        )
        community_alias2.user = community_user
        self.session.add_all([community_alias1, community_alias2])
        self.session.commit()

        self.assertSetEqual(set(community_user.aliases), {community_alias1, community_alias2})

        app1.community_user_alias = community_alias1
        app2.community_user_alias = community_alias2
        self.session.commit()

        self.assertEqual(app1.community_user_alias_id, community_alias1.id)
        self.assertEqual(app2.community_user_alias_id, community_alias2.id)
        self.assertEqual(app1.community_user_alias.user_id, app2.community_user_alias.user_id)

    def test_communisms(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()

        communism = models.Communism(
            amount=42,
            creator_id=1,
            externals=1
        )
        self.session.add(communism)
        self.session.commit()
        self.assertIsNotNone(communism.creator)
        self.assertIs(communism, self.session.query(models.Communism).first())

        self.session.add_all([
            models.CommunismUsers(communism_id=communism.id, user_id=1, quantity=1),
            models.CommunismUsers(communism_id=communism.id, user_id=2, quantity=2),
            models.CommunismUsers(communism_id=communism.id, user_id=3, quantity=3)
        ])
        self.session.commit()
        self.assertEqual(6, sum([u.quantity for u in communism.participants]))
        self.assertEqual(3, len(self.session.query(models.CommunismUsers).all()))

        new_participant = models.CommunismUsers(user_id=4, quantity=4)
        communism.participants.append(new_participant)
        self.session.commit()
        self.assertEqual(10, sum([u.quantity for u in communism.participants]))
        self.assertEqual(4, len(self.session.query(models.CommunismUsers).all()))
        self.assertEqual(4, len(self.session.query(models.Communism).get(1).participants))
        self.assertEqual(4, new_participant.id)
        self.assertIs(new_participant.user, self.session.query(models.User).get(4))

        lonely_participant = models.CommunismUsers(communism_id=2, user_id=3, quantity=3)
        self.session.add(lonely_participant)
        self.session.commit()
        self.assertEqual(5, len(self.session.query(models.CommunismUsers).all()))
        self.assertEqual(4, len(self.session.query(models.Communism).get(1).participants))
        self.assertIs(lonely_participant.user, self.session.query(models.User).get(3))

        self.assertEqual(1, self.session.query(models.Communism).get(1).externals)
        communism.externals += 1
        self.session.commit()
        self.assertEqual(2, self.session.query(models.Communism).get(1).externals)

        self.session.delete(communism)
        self.session.commit()
        self.assertEqual(1, len(self.session.query(models.CommunismUsers).all()))
        self.assertIsNone(self.session.query(models.Communism).get(1))
        self.assertListEqual([], self.session.query(models.Communism).all())
        self.assertEqual(5, lonely_participant.id)

        try:
            self.assertIsNotNone(repr(communism.participants))
            self.fail()
        except sqlalchemy.orm.exc.DetachedInstanceError as exc:
            self.assertTrue(exc)

        try:
            self.session.add(communism)
            self.session.commit()
            self.fail()
        except sqlalchemy.exc.InvalidRequestError as exc:
            self.assertTrue(exc)
            self.session.rollback()

        new_communism = models.Communism(
            active=False,
            amount=6,
            description="new communism",
            creator_id=5
        )
        self.session.add(new_communism)
        self.session.commit()
        self.assertEqual(1, new_communism.id)
        self.assertEqual(communism.id, new_communism.id)
        self.assertIsNotNone(new_communism.creator)

        new_communism.creator_id = 42
        self.session.commit()
        self.assertIsNone(new_communism.creator)

    def test_delete_consumable_with_messages_cascading(self):
        consumable = models.Consumable(
            name="Mate",
            description="everyone hates Mate",
            price=9000,
            symbol="X",
            stock=42
        )
        self.session.add(consumable)
        self.session.commit()
        self.assertIs(self.session.query(models.Consumable).first(), consumable)
        self.assertEqual(1, len(self.session.query(models.Consumable).all()))

        self.session.add_all([
            models.ConsumableMessage(message="A", consumable_id=consumable.id),
            models.ConsumableMessage(message="B", consumable_id=consumable.id),
            models.ConsumableMessage(message="C", consumable_id=consumable.id),
        ])
        self.session.commit()
        self.assertEqual(3, len(self.session.query(models.ConsumableMessage).all()))

        self.session.delete(consumable)
        self.session.commit()
        self.assertEqual(0, len(self.session.query(models.Consumable).all()))
        self.assertEqual(0, len(self.session.query(models.ConsumableMessage).all()))


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
