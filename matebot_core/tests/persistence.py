"""
MateBot database unit tests
"""

import datetime
import unittest

import sqlalchemy
import sqlalchemy.orm
from sqlalchemy.engine import Engine as _Engine

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


class DatabaseUsabilityTests(_BaseDatabaseTests):
    """
    Database test cases checking the correct usability of the models
    """

    @staticmethod
    def get_sample_users():
        user1 = models.User(name="user1", balance=-42, external=True)
        user2 = models.User(name="user2", balance=51, external=False)
        user3 = models.User(external=True)
        user3.name = "user3"
        user4 = models.User(name="user4", balance=2, external=False)
        user5 = models.User(permission=False, active=False, external=False, voucher_id=2)
        return [user1, user2, user3, user4, user5]

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
        user1, user2, user3, user4, _ = self.get_sample_users()
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

    def test_insert_all_sample_users(self):
        self.session.add_all(self.get_sample_users())
        self.session.commit()
        self.assertEqual(len(self.get_sample_users()), len(self.session.query(models.User).all()))


class DatabaseRestrictionTests(_BaseDatabaseTests):
    """
    Database test cases checking restrictions on certain operations (constraints)
    """


class DatabaseSchemaTests(_BaseDatabaseTests):
    """
    Database test cases checking the returned schemas of the database models
    """


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for cls in [DatabaseUsabilityTests, DatabaseRestrictionTests, DatabaseSchemaTests]:
        for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
            suite.addTest(cls(fixture))
    return suite


if __name__ == '__main__':
    unittest.main()
