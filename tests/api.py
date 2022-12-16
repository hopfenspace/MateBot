"""
MateBot unit tests for the whole API in certain user actions
"""

import time
import urllib.parse
import unittest as _unittest
from typing import List

from matebot_core import schemas as _schemas
from matebot_core.persistence import models

from . import utils


class APITests(utils.BaseAPITests):
    def test_basic_endpoints_and_redirects_to_docs(self):
        for _ in range(64):
            self.assertEqual({}, self.assertQuery(("GET", "/health"), 200).json())

        self.assertIn("docs", self.assertQuery(
            ("GET", "/"),
            [302, 303, 307],
            allow_redirects=False,
            r_is_json=False
        ).headers.get("Location"))

        self.assertEqual(1, len(self.assertQuery(("GET", "/"), r_is_json=False).history))
        self.assertEqual(
            self.assertQuery(("GET", "/"), r_is_json=False, no_version=True).content,
            self.assertQuery(("GET", "/docs"), r_is_json=False, no_version=True).content
        )
        self.assertQuery(("GET", "/openapi.json"), r_headers={"Content-Type": "application/json"})
        self.assertQuery(("GET", "/openapi.json"), r_headers={"Content-Type": "application/json"}, no_version=True)

        self.assertQuery(("GET", "/status"), 404)
        self.assertQuery(("POST", "/status"), 404)

    def test_pagination(self):
        def _test(**kwargs) -> List[int]:
            path = "/users"
            args = urllib.parse.urlencode(kwargs)
            if args:
                path += "?" + args
            return [int(obj["id"]) for obj in self.assertQuery(("GET", path), 200).json()]

        self.make_special_user()
        self.login()
        for i in range(9):
            self.assertQuery(("POST", "/users"), 201, json={"name": f"user{i}"}, r_schema=_schemas.User)
        with self.get_db_session() as session:
            for j in range(9):
                session.add(models.User(name=f"user{9+j}", external=False, permission=True))
                session.commit()

        self.assertEqual(19, len(_test()))
        self.assertEqual(0, len(_test(name="foo")))
        self.assertEqual(0, len(_test(name="bar")))
        self.assertEqual(1, len(_test(name="Community")))
        self.assertEqual(0, len(_test(name="Community", community=False)))
        self.assertEqual(1, len(_test(name="Community", community=True)))
        self.assertEqual(1, len(_test(name="user2")))
        self.assertEqual(1, len(_test(name="user6")))
        self.assertEqual(1, len(_test(name="user12")))
        self.assertSetEqual(set(_test()), set(_test(descending=True)))
        self.assertListEqual(_test(page=2, descending=True)[::-1], _test(page=2, descending=False))
        self.assertSetEqual(set(_test()), set(_test(page=873)))
        self.assertEqual(4, len(_test(limit=4)))
        self.assertEqual(8, len(_test(limit=8)))
        self.assertEqual(19, len(_test(limit=82)))
        self.assertEqual(5, len(_test(limit=5, page=1)))
        self.assertEqual(5, len(_test(limit=5, page=2)))
        self.assertEqual(0, len(_test(limit=5, page=27)))
        self.assertEqual(2, len(_test(limit=2, page=0)))
        self.assertEqual(2, len(_test(limit=2, page=7)))
        self.assertEqual(1, len(_test(limit=1, page=18)))
        self.assertEqual(0, len(_test(limit=1, page=19)))
        self.assertListEqual([15, 16], _test(limit=2, page=7))
        self.assertListEqual([5, 4], _test(limit=2, page=7, descending=True))
        self.assertListEqual([1], _test(limit=1, page=18, descending=True))
        self.assertListEqual([19], _test(limit=1, page=18, descending=False))
        self.assertListEqual([], _test(limit=2, page=18))
        self.assertListEqual([15, 16, 17, 18, 19], _test(limit=14, page=1))
        self.assertListEqual([5, 4, 3, 2, 1], _test(limit=14, page=1, descending=True))
        self.assertListEqual([], _test(limit=14, page=2, descending=True))
        self.assertListEqual([3, 2, 1], _test(limit=16, page=1, descending=True))
        self.assertListEqual([1, 2, 3], _test(limit=3, page=0, descending=False))
        self.assertListEqual([10, 11, 12], _test(limit=3, page=3))
        self.assertListEqual([11, 12, 13], _test(limit=3, page=3, community=False))
        self.assertListEqual([], _test(limit=3, page=3, id=2))
        self.assertListEqual([], _test(limit=3, page=3, external=True))
        self.assertListEqual([19], _test(limit=3, page=3, external=False))
        self.assertListEqual([1, 11, 12], _test(limit=3, external=False))
        self.assertListEqual([8, 9, 10], _test(limit=3, page=2, external=True))
        self.assertListEqual([4, 3, 2], _test(limit=3, page=2, external=True, descending=True))
        self.assertListEqual([16, 17, 18], _test(limit=3, page=2, external=False))
        self.assertListEqual([13, 12, 11], _test(limit=3, page=2, external=False, descending=True))
        self.assertListEqual([1, 11], _test(limit=2, external=False))
        self.assertListEqual([1, 11, 12, 13, 14, 15, 16, 17, 18, 19], _test(page=1, external=False))
        self.assertListEqual([19, 18, 17, 16, 15, 14, 13, 12, 11, 1], _test(page=1, external=False, descending=True))
        self.assertListEqual([17, 16], _test(limit=2, page=1, external=False, descending=True))

    def test_username_changes(self):
        self.login()
        self.assertEqual(
            self.assertQuery(("GET", "/users"), 200).json(),
            self.assertQuery(("GET", "/users?community=true"), 200).json()
        )

        users = []
        for i in range(10):
            user = self.assertQuery(("POST", "/users"), 201, json={"name": f"user{i}"}, r_schema=_schemas.User).json()
            del user["modified"]
            users.append(user)

        self.assertQuery(
            ("POST", "/callbacks"), 201,
            json={"url": f"http://localhost:{self.callback_server_port}/"}
        )

        def f(index: int, name: str):
            def q(x):
                del x["modified"]
                return x
            users[index]["name"] = name
            self.assertListEqual(users, [q(e) for e in self.assertQuery(("GET", "/users?community=false"), 200).json()])

        self.assertEqual("foo", self.assertQuery(
            ("POST", "/users/setName"), 200, json={"issuer": 2, "name": "foo"}, r_schema=_schemas.User
        ).json()["name"])
        f(0, "foo")
        self.assertEqual("bar", self.assertQuery(
            ("POST", "/users/setName"), 200, json={"issuer": 3, "name": "bar"}, r_schema=_schemas.User
        ).json()["name"])
        f(1, "bar")
        self.assertEqual("baz", self.assertQuery(
            ("POST", "/users/setName"), 200, json={"issuer": 3, "name": "baz"}, r_schema=_schemas.User
        ).json()["name"])
        f(1, "baz")
        self.assertEqual("bar", self.assertQuery(
            ("POST", "/users/setName"), 200, json={"issuer": 3, "name": "bar"}, r_schema=_schemas.User
        ).json()["name"])
        f(1, "bar")
        self.assertIn("not available", self.assertQuery(
            ("POST", "/users/setName"), 400, json={"issuer": 4, "name": "bar"}, r_schema=_schemas.APIError
        ).json()["message"])
        f(1, "bar")
        self.assertIn("not available", self.assertQuery(
            ("POST", "/users/setName"), 400, json={"issuer": 7, "name": "user4"}, r_schema=_schemas.APIError
        ).json()["message"])
        f(1, "bar")

    def test_users(self):
        self.login()
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=true"), 200).json()))
        self.assertListEqual([], self.assertQuery(("GET", "/users?community=false"), 200).json())

        # Creating a set of test users
        users = []
        for i in range(1, 11):
            user = self.assertQuery(("POST", "/users"), 201, json={"name": f"user{i}"}, r_schema=_schemas.User).json()
            self.assertEqual(i+1, user["id"])
            self.assertEqual(
                user,
                self.assertQuery(("GET", f"/users?id={i+1}"), 200).json()[0]
            )
            self.assertEqual(user["name"], f"user{i}")
            users.append(user)
            self.assertEqual(
                users,
                self.assertQuery(("GET", "/users?community=false"), 200).json()
            )

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"url": f"http://localhost:{self.callback_server_port}/"}
        )

        # Deleting users should not work by 'DELETE' but with disabling via 'POST'
        self.assertQuery(
            ("DELETE", "/users"),
            [405, 409],
            json=users[-1]
        )
        j = len(users) - 1
        self.assertQuery(
            ("POST", f"/users/delete"),
            200,
            json={"id": j, "issuer": j},
            r_schema=_schemas.User
        )
        self.assertEvent("user_softly_deleted", {"id": j}, timeout=5)

        user0 = users[0]
        user1 = users[1]
        user2 = users[2]

        # TODO: Updating the permission external flags should work

        # TODO: Check that voucher handling works as expected

        # Transactions from/to disabled users should fail
        self.assertQuery(
            ("POST", "/transactions/send"),
            400,
            json={
                "sender": j,
                "receiver": user1["id"],
                "amount": 42,
                "reason": "test"
            }
        )
        self.assertQuery(
            ("POST", "/transactions/send"),
            400,
            json={
                "sender": user1["id"],
                "receiver": j,
                "amount": 42,
                "reason": "test"
            }
        )

        # Deleting users with balance != 0 should fail
        self.assertEqual(0, self.assertQuery(("GET", f"/users?id={user0['id']}"), 200).json()[0]["balance"])
        self.assertEqual(0, self.assertQuery(("GET", f"/users?id={user2['id']}"), 200).json()[0]["balance"])
        self._edit_user(user0["id"], external=False)
        self._edit_user(user2["id"], external=False)
        self.assertQuery(
            ("POST", "/transactions/send"),
            201,
            json={
                "sender": user0["id"],
                "receiver": user2["id"],
                "amount": 42,
                "reason": "test"
            }
        )
        self.assertEvent("transaction_created", {"id": 1, "sender": user0["id"], "receiver": user2["id"], "amount": 42})
        user0 = self.assertQuery(("GET", f"/users?id={user0['id']}"), 200).json()[0]
        user2 = self.assertQuery(("GET", f"/users?id={user2['id']}"), 200).json()[0]
        self.assertEqual(user0["balance"], -user2["balance"])
        self.assertQuery(("POST", "/users/delete"), 400, json={"id": user0['id']})
        self.assertQuery(("POST", "/users/delete"), 400, json={"id": user0['id'], "issuer": user0['id']})

        # Deleting the user after fixing the balance should work again
        self.assertQuery(
            ("POST", "/transactions/send"),
            201,
            json={
                "sender": user2["id"],
                "receiver": user0["id"],
                "amount": 42,
                "reason": "reverse"
            }
        )
        user0 = self.assertQuery(("GET", f"/users?id={user0['id']}"), 200).json()[0]
        user2 = self.assertQuery(("GET", f"/users?id={user2['id']}"), 200).json()[0]
        self.assertEqual(user0["balance"], 0)
        self.assertEqual(user2["balance"], 0)
        self.assertEvent("transaction_created", {"id": 2, "sender": user2["id"], "receiver": user0["id"], "amount": 42})
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user0["id"], "issuer": user0["id"]}
        )
        self.assertEvent("user_softly_deleted", {"id": user0["id"]})
        self.assertQuery(
            ("POST", "/users/delete"),
            400,
            json={"id": user2["id"]}
        )
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user2["id"], "issuer": user2["id"]}
        )
        self.assertEvent("user_softly_deleted", {"id": user2["id"]})
        users.pop(0)
        users.pop(0)
        users.pop(0)

        # Deleting users that created/participate in an active communism shouldn't work
        user0 = users[0]
        user1 = users[1]
        self._edit_user(user0["id"], external=False)
        communism = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 1337,
                "description": "description",
                "creator": user0["id"],
                "participants": [{"quantity": 1, "user_id": user1["id"]}]
            }
        ).json()
        self.assertEvent("communism_created", {"id": 1, "user": user0["id"], "amount": 1337, "participants": 1})
        self.assertQuery(("POST", "/users/delete"), 400, json={"id": user0['id']})
        self.assertQuery(("POST", "/users/delete"), 400, json={"id": user1["id"]})
        self.assertListEqual([communism], self.assertQuery(("GET", "/communisms"), 200).json())

        # Deleting users that don't participate in active communisms should work
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user1["id"], "issuer": user1["id"]}
        )
        self.assertEvent("user_softly_deleted", {"id": user1["id"]})
        self.assertQuery(
            ("POST", "/communisms/abort"),
            200,
            json={"id": 1, "issuer": user0["id"]},
            r_schema=_schemas.Communism
        )
        self.assertEvent("communism_closed", {"id": 1, "transactions": 0, "aborted": True, "participants": 1})
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user0["id"], "issuer": user0["id"]}
        )
        self.assertEvent("user_softly_deleted", {"id": user0["id"]})
        users.pop(0)
        users.pop(1)

        self.assertEqual(len(self.assertQuery(("GET", "/users?community=false"), 200).json()), 10)

        # Check that deleting users with positive balance transfers the remaining amount to the community user
        self.make_special_user()
        user_to_delete_id = int(
            self.assertQuery(("POST", "/users"), 201, json={"name": "foo"}, r_schema=_schemas.User).json()["id"]
        )
        old_community_balance = self.assertQuery(("GET", "/users?community=1"), 200).json()[0]["balance"]
        session = self.get_db_session()
        user_to_delete = session.get(models.User, user_to_delete_id)
        user_to_delete.balance = 1337
        session.add(user_to_delete)
        session.commit()
        self.assertQuery(("POST", "/users/delete"), 400, json={"id": user_to_delete_id})
        user = self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user_to_delete_id, "issuer": user_to_delete_id}
        ).json()
        self.assertEqual(user["balance"], 0)
        new_community_balance = self.assertQuery(("GET", "/users?community=1"), 200).json()[0]["balance"]
        self.assertEqual(old_community_balance + 1337, new_community_balance)

    def test_alias_deletion(self):
        self.make_special_user()
        self.login()
        with self.get_db_session() as session:
            session.add(models.User(name="A", external=False, permission=True))
            session.add(models.User(name="B", external=True))
            session.commit()

            session.add(models.Application(name="app1", password="app1", salt="app1"))
            session.add(models.Application(name="app2", password="app2", salt="app2"))
            session.add(models.Application(name="app3", password="app3", salt="app3"))
            session.commit()

            session.add(models.Alias(user_id=2, application_id=1, username="2-1", confirmed=True))
            session.add(models.Alias(user_id=2, application_id=2, username="2-2", confirmed=True))
            session.add(models.Alias(user_id=2, application_id=3, username="2-3", confirmed=True))
            session.add(models.Alias(user_id=3, application_id=1, username="3-1", confirmed=True))
            session.add(models.Alias(user_id=3, application_id=2, username="3-2", confirmed=True))
            session.add(models.Alias(user_id=3, application_id=3, username="3-3", confirmed=True))
            session.commit()

        self.assertEqual(6, len(self.assertQuery(("GET", "/aliases"), 200).json()))
        self.assertQuery(("POST", "/aliases/delete"), 400, r_schema=_schemas.APIError)
        self.assertQuery(("POST", "/aliases/delete"), 400, json={"id": 1, "issuer": 3}, r_schema=_schemas.APIError)
        self.assertQuery(("POST", "/aliases/delete"), 400, json={"id": 2, "issuer": 3}, r_schema=_schemas.APIError)
        self.assertQuery(("POST", "/aliases/delete"), 400, json={"id": 4, "issuer": 1}, r_schema=_schemas.APIError)
        self.assertQuery(("POST", "/aliases/delete"), 400, json={"id": 4, "issuer": 2}, r_schema=_schemas.APIError)
        self.assertEqual(6, len(self.assertQuery(("GET", "/aliases"), 200).json()))
        deletion1 = self.assertQuery(
            ("POST", "/aliases/delete"), 200,
            json={"id": 2, "issuer": 2}, r_schema=_schemas.AliasDeletion
        ).json()
        self.assertEqual(deletion1["user_id"], 2)
        self.assertEqual(5, len(self.assertQuery(("GET", "/aliases"), 200).json()))
        deletion2 = self.assertQuery(
            ("POST", "/aliases/delete"), 200,
            json={"id": 6, "issuer": "3-1"}, r_schema=_schemas.AliasDeletion
        ).json()
        self.assertEqual(deletion2["user_id"], 3)
        self.assertListEqual(deletion2["aliases"], [
            {"id": 4, "user_id": 3, "application_id": 1, "username": "3-1", "confirmed": True},
            {"id": 5, "user_id": 3, "application_id": 2, "username": "3-2", "confirmed": True}
        ])
        self.assertEqual(4, len(self.assertQuery(("GET", "/aliases"), 200).json()))

    def test_externals_vouch_for_externals(self):
        self.make_special_user()
        self.login()
        user1 = self.assertQuery(("POST", "/users"), 201, json={"name": "foo"}, r_schema=_schemas.User).json()
        user2 = self.assertQuery(("POST", "/users"), 201, json={"name": "bar"}, r_schema=_schemas.User).json()

        def _check():
            self.assertEqual(user1["external"], True)
            self.assertEqual(user1["permission"], False)
            self.assertEqual(user1["active"], True)
            self.assertEqual(user1["voucher_id"], None)
            self.assertEqual(user2["external"], True)
            self.assertEqual(user2["permission"], False)
            self.assertEqual(user2["active"], True)
            self.assertEqual(user2["voucher_id"], None)

        _check()
        self.assertTrue(self.assertQuery(
            ("POST", "/users/setVoucher"),
            400,
            json={"debtor": user1["id"], "voucher": user2["id"], "issuer": user2["id"]}
        ).json()["error"])
        user1 = self.assertQuery(("GET", f"/users?id={user1['id']}"), 200).json()[0]
        user2 = self.assertQuery(("GET", f"/users?id={user2['id']}"), 200).json()[0]
        _check()

    def test_refunds(self):
        self.make_special_user()
        self.login()
        community = self.assertQuery(("GET", "/users?community=1"), 200).json()
        self.assertEqual(len(community), 1)
        community = community[0]
        self.assertListEqual([], self.assertQuery(("GET", "/refunds"), 200).json())
        self.assertEqual(len(self.assertQuery(("GET", "/votes"), 200).json()), 0)

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"url": f"http://localhost:{self.callback_server_port}/"}
        )

        # Adding the creator user
        self.assertQuery(("POST", "/users"), 201, json={"name": "user"}, r_schema=_schemas.User).json()

        # Checking for the permission
        self.assertQuery(
            ("POST", "/refunds"),
            400,
            json={"description": "Do you like this?", "amount": 42, "creator": 2}
        )
        self._edit_user(2, permission=True, external=False)

        # Create the first refund request
        refund1 = self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Do you like this?", "amount": 42, "creator": 2},
            r_schema=_schemas.Refund
        ).json()
        self.assertEqual(refund1["id"], 1)
        self.assertEqual(refund1["active"], True)
        self.assertEqual(refund1["ballot_id"], 1)
        self.assertEqual(refund1["votes"], [])
        self.assertEvent("refund_created", ["id", "user"])

        # Add another refund request to be sure
        refund2 = self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Are you sure?", "amount": 1337, "creator": 2}
        ).json()
        self.assertEqual(refund2["id"], 2)
        self.assertEqual(refund2["votes"], [])
        self.assertEqual(refund2["allowed"], None)
        self.assertEqual(refund2["transaction"], None)
        self.assertEqual(refund2["active"], True)
        self.assertEvent("refund_created", {"id": 2, "amount": 1337, "user": 2})

        # Abort the second refund request
        self.assertQuery(
            ("POST", "/refunds/abort"),
            400,
            json={"id": 2, "issuer": 1}
        ).json()
        refund2 = self.assertQuery(
            ("POST", "/refunds/abort"),
            200,
            json={"id": 2, "issuer": 2}
        ).json()
        self.assertEqual(refund2["allowed"], False)
        self.assertEqual(refund2["transaction"], None)
        self.assertEqual(refund2["active"], False)
        self.assertEvent("refund_closed", {"id": 2, "aborted": True, "accepted": False})

        # A user can't vote on its own refund requests
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user": 2, "ballot_id": 1, "vote": True}
        )

        # Adding an unprivileged user
        u = self.assertQuery(("POST", "/users"), 201, json={"name": "user1"}, r_schema=_schemas.User).json()
        self.assertEqual(u["external"], True)
        self.assertEqual(u["permission"], False)
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user": 3, "ballot_id": 1, "vote": True}
        )

        # Adding a privileged user which gets disabled first, though
        self.assertQuery(("POST", "/users"), 201, json={"name": "user2"}, r_schema=_schemas.User).json()
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": 4, "issuer": 4}
        )
        self.assertEvent("user_softly_deleted", ["id"])
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user": 4, "ballot_id": 1, "vote": True}
        )

        # Adding a new user to actually vote on the refund for the first time
        self.assertQuery(("POST", "/users"), 201, json={"name": "user3"}, r_schema=_schemas.User).json()
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user": 5, "ballot_id": 1, "vote": True}
        )
        self._edit_user(5, permission=True, external=False)
        vote1 = self.assertQuery(
            ("POST", "/refunds/vote"),
            200,
            json={"user": 5, "ballot_id": 1, "vote": True},
            r_schema=_schemas.RefundVoteResponse
        ).json()
        self.assertEqual(vote1["vote"]["vote"], True)
        self.assertEqual(vote1["vote"]["ballot_id"], 1)
        self.assertIsNone(vote1["refund"]["transaction"])
        self.assertGreaterEqual(vote1["refund"]["modified"], refund1["created"])
        self.assertListEqual(vote1["refund"]["votes"], [vote1["vote"]])
        self.assertEvent("refund_updated", {"id": 1, "last_vote": 1, "current_result": 1})

        # The community user shouldn't vote on refund requests
        self.assertQuery(
            ("POST", "/refunds/vote"),
            [400, 409],
            json={"user": community["id"], "ballot_id": 1, "vote": True}
        )

        # Add another user to accept the refund request
        old_balance = self.assertQuery(("GET", "/users?id=2"), 200).json()[0]["balance"]
        self.assertQuery(("POST", "/users"), 201, json={"name": "user4"}, r_schema=_schemas.User).json()
        self._edit_user(6, permission=True)
        vote2 = self.assertQuery(
            ("POST", "/refunds/vote"),
            200,
            json={"user": 6, "ballot_id": 1, "vote": True},
            r_schema=_schemas.RefundVoteResponse
        ).json()
        self.assertListEqual(vote2["refund"]["votes"], [vote1["vote"], vote2["vote"]])
        self.assertIsNotNone(vote2["refund"]["transaction"])
        self.assertEvent("refund_updated", {"id": 1, "last_vote": 2, "current_result": 2})
        transaction = _schemas.Transaction(**vote2["refund"]["transaction"])
        self.assertEvent("refund_closed", {"id": 1, "aborted": False, "accepted": True, "transaction": transaction.id})
        self.assertEqual(transaction.amount, 42)
        self.assertEqual(transaction.sender.id, 1)
        self.assertEqual(transaction.receiver.id, 2)
        self.assertIsNone(transaction.multi_transaction_id)
        self.assertEqual(vote2["refund"]["allowed"], True)
        self.assertEqual(vote2["refund"]["active"], False)

        new_balance = self.assertQuery(("GET", "/users?id=2"), 200).json()[0]["balance"]
        self.assertGreater(new_balance, old_balance)
        self.assertEqual(new_balance, old_balance + 42)
        transactions = self.assertQuery(("GET", "/transactions"), 200).json()
        self.assertListEqual([transaction], transactions)

        # Don't allow to add votes to already closed refund requests
        self.assertQuery(("POST", "/users"), 201, json={"name": "user5"}, r_schema=_schemas.User).json()
        self.assertQuery(("POST", "/refunds/vote"), 400, json={"user": 7, "ballot_id": 1, "vote": True})

        # The community user shouldn't create refunds
        self.assertQuery(
            ("POST", "/refunds"),
            409,
            json={"description": "Foo", "amount": 1337, "creator": community["id"]}
        )

        # User referenced by 'creator' doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/refunds"),
            400,
            json={"description": "Foo", "amount": 1337, "creator": 8}
        ).json()
        self.assertQuery(("POST", "/users"), 201, json={"name": "user6"}, r_schema=_schemas.User).json()
        self.assertQuery(
            ("POST", "/users/setVoucher"),
            200,
            json={"debtor": 8, "voucher": 2, "issuer": 2}
        )
        self.assertEvent("voucher_updated", {"id": 8, "voucher": 2})
        self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Foo", "amount": 1337, "creator": 8}
        ).json()

        # Check that a vote for a poll can't be used on the refunds endpoints
        poll_ballot_id = self.assertQuery(
            ("POST", "/polls"), 201,
            json={"issuer": 5, "user": 3, "variant": "get_internal"}
        ).json()["ballot_id"]
        self.assertEvent("poll_created")
        self.assertQuery(
            ("POST", "/polls/vote"), 200,
            json={"user": 6, "ballot_id": poll_ballot_id, "vote": True}
        )
        self.assertQuery(
            ("POST", "/refunds/vote"), 409,
            json={"user": 5, "ballot_id": poll_ballot_id, "vote": True}
        )

    def test_polls(self):
        self.login()
        self.make_special_user()
        self.assertListEqual([], self.assertQuery(("GET", "/polls"), 200).json())

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"url": f"http://localhost:{self.callback_server_port}/"}
        )

        # Create a set of sample users with various attributes
        session = self.get_db_session()
        self.assertEqual(1, len(session.query(models.Application).all()))
        self.assertEqual(1, session.query(models.Application).all()[0].id)
        user1_model = models.User(name="user1", external=False, permission=True)
        user2_model = models.User(name="user2", external=False, permission=True)
        user3_model = models.User(name="user3", external=False, permission=False)
        user4_model = models.User(name="user4", external=False, permission=False)
        user5_model = models.User(name="user5", external=True, permission=False, voucher_user=user1_model)
        user6_model = models.User(name="user6", external=True, permission=False, voucher_user=None)
        user7_model = models.User(name="user7", external=False, permission=True, active=False)
        user8_model = models.User(name="user8", external=True, active=False)
        alias1_model = models.Alias(application_id=1, username="user1", confirmed=True)
        alias2_model = models.Alias(application_id=1, username="user2", confirmed=False)
        alias3_model = models.Alias(application_id=1, username="user3", confirmed=True)
        alias1, alias2, alias3 = alias1_model.username, alias2_model.username, alias3_model.username
        user1_model.aliases, user2_model.aliases, user3_model.aliases = ([alias1_model], [alias2_model], [alias3_model])
        session.add_all([
            user1_model, user2_model, user3_model, user4_model, user5_model, user6_model, user7_model, user8_model,
            alias1_model, alias2_model, alias3_model
        ])
        session.commit()
        user1, user2, user3, user4 = user1_model.id, user2_model.id, user3_model.id, user4_model.id
        user5, user6, user7, user8 = user5_model.id, user6_model.id, user7_model.id, user8_model.id
        session.close()
        self.assertEqual(9, len(self.assertQuery(("GET", "/users"), 200).json()))
        self.assertEqual(3, len(self.assertQuery(("GET", "/aliases"), 200).json()))
        self.assertEqual(2, len(self.assertQuery(("GET", "/aliases?confirmed=true"), 200).json()))

        # Check various bad configurations
        self.assertQuery(
            ("POST", "/polls"), 409,
            json={"user": 1, "issuer": user6, "variant": "get_internal"}
        )
        self.assertQuery(
            ("POST", "/polls"), 400,
            json={"user": user1, "issuer": user6, "variant": "get_permissions"}
        )
        self.assertQuery(
            ("POST", "/polls"), 400,
            json={"user": user5, "issuer": user1, "variant": "loose_permissions"}
        )
        self.assertQuery(
            ("POST", "/polls"), 400,
            json={"user": user6, "issuer": user6, "variant": "get_permissions"}
        )
        self.assertQuery(
            ("POST", "/polls"), 400,
            json={"user": user1, "issuer": user6, "variant": "loose_internal"}
        )
        self.assertQuery(
            ("POST", "/polls"), 400,
            json={"user": user3, "issuer": user1, "variant": "get_internal"}
        )
        self.assertQuery(
            ("POST", "/polls"), 400,
            json={"user": user1, "issuer": user3, "variant": "get_permissions"}
        )
        self.assertQuery(
            ("POST", "/polls"), 400,
            json={"user": user1, "issuer": user5, "variant": "loose_permission"}
        )

        # Create some correct polls
        get_internal = self.assertQuery(
            ("POST", "/polls"), 201,
            json={"user": user6, "issuer": user6, "variant": "get_internal"}
        ).json()
        self.assertEvent("poll_created", ["id", "user", "variant"])
        get_internal2 = self.assertQuery(
            ("POST", "/polls"), 201,
            json={"user": user5, "issuer": user2, "variant": "get_internal"}
        ).json()
        self.assertEvent("poll_created")
        get_permission = self.assertQuery(
            ("POST", "/polls"), 201,
            json={"user": user3, "issuer": user3, "variant": "get_permission"}
        ).json()
        self.assertEvent("poll_created", {"id": 3, "user": user3, "variant": "get_permission"})
        loose_internal = self.assertQuery(
            ("POST", "/polls"), 201,
            json={"user": user4, "issuer": user2, "variant": "loose_internal"}
        ).json()
        self.assertEvent("poll_created")
        loose_permission = self.assertQuery(
            ("POST", "/polls"), 201,
            json={"user": user1, "issuer": user2, "variant": "loose_permission"}
        ).json()
        self.assertEvent("poll_created")
        self.assertEqual(5, len(self.assertQuery(("GET", "/polls"), 200).json()))
        self.assertEqual(5, len(self.assertQuery(("GET", "/polls?active=true"), 200).json()))
        self.assertEqual(0, len(self.assertQuery(("GET", "/polls?active=false"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/polls?ballot_id=4"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/polls?user_id=4"), 200).json()))
        self.assertEqual(0, len(self.assertQuery(("GET", "/polls?user_id=3"), 200).json()))

        # Perform some invalid vote requests
        self.assertQuery(
            ("POST", "/polls/vote"), 400,
            # Don't vote on your own polls
            json={"user": user6, "ballot_id": get_internal["id"], "vote": False}
        )
        self.assertQuery(
            ("POST", "/polls/vote"), 400,
            # Don't vote on other polls when you don't have permissions
            json={"user": user6, "ballot_id": loose_permission["id"], "vote": False}
        )
        self.assertQuery(
            ("POST", "/polls/vote"), 400,
            # Don't vote on other polls when you don't have permissions
            json={"user": user4, "ballot_id": get_internal["id"], "vote": False}
        )
        self.assertQuery(
            ("POST", "/polls/vote"), 400,
            # Don't vote on your own polls
            json={"user": user1, "ballot_id": loose_permission["id"], "vote": False}
        )
        self.assertQuery(
            ("POST", "/polls/vote"), 400,
            # Don't vote on your own polls
            json={"user": alias1, "ballot_id": loose_permission["id"], "vote": False}
        )
        self.assertQuery(
            ("POST", "/polls/vote"), 400,
            # Don't vote when the user account has been disabled
            json={"user": user7, "ballot_id": get_permission["id"], "vote": False}
        )

        # Check that a vote for a refund can't be used on the polls endpoints
        self.assertQuery(("POST", "/refunds"), 201, json={"amount": 4, "creator": 3, "description": "foo"})
        self.assertEvent("refund_created")
        self.assertQuery(
            ("POST", "/polls/vote"), 409,
            json={"user": 4, "ballot_id": 6, "vote": True}
        )

        # Add one vote of user1 to include user6
        self.assertEqual(0, len(self.assertQuery(("GET", f"/polls?id={get_internal['id']}")).json()[0]["votes"]))
        self.assertQuery(
            ("POST", "/polls/vote"), 200,
            json={"user": alias1, "ballot_id": get_internal["id"], "vote": True}
        )
        self.assertQuery(
            ("POST", "/polls/vote"), 400,
            # Don't vote twice
            json={"user": user1, "ballot_id": get_internal["id"], "vote": False}
        )
        self.assertEqual(1, len(self.assertQuery(("GET", f"/polls?id={get_internal['id']}")).json()[0]["votes"]))
        self.assertIsNone(self.assertQuery(("GET", f"/polls?id={get_internal['id']}")).json()[0]["accepted"])
        self.assertTrue(self.assertQuery(("GET", f"/polls?id={get_internal['id']}")).json()[0]["active"])
        self.assertEvent("poll_updated")

        # Add one vote of user2 to include user6 which should close & accept the poll
        self.assertTrue(self.assertQuery(("GET", f"/users?id={user6}")).json()[0]["external"])
        self.assertQuery(
            ("POST", "/polls/vote"), 200,
            json={"user": user2, "ballot_id": get_internal["id"], "vote": True}
        )
        self.assertTrue(self.assertQuery(("GET", f"/polls?id={get_internal['id']}")).json()[0]["accepted"])
        self.assertFalse(self.assertQuery(("GET", f"/polls?id={get_internal['id']}")).json()[0]["active"])
        self.assertEvent("poll_updated")
        self.assertEvent("poll_closed", ["id", "user", "accepted", "aborted", "variant", "last_vote"])
        self.assertFalse(self.assertQuery(("GET", f"/users?id={user6}")).json()[0]["external"])
        self.assertIsNone(self.assertQuery(("GET", f"/users?id={user6}")).json()[0]["voucher_id"])

        # Check that accepting an external to become internal clears the voucher
        self.assertTrue(self.assertQuery(("GET", f"/users?id={user5}")).json()[0]["external"])
        self.assertIsNotNone(self.assertQuery(("GET", f"/users?id={user5}")).json()[0]["voucher_id"])
        self.assertEqual(0, len(self.assertQuery(("GET", f"/polls?id={get_internal2['id']}")).json()[0]["votes"]))
        self.assertQuery(
            ("POST", "/polls/vote"), 200,
            json={"user": alias1, "ballot_id": get_internal2["id"], "vote": True}
        )
        self.assertEqual(1, len(self.assertQuery(("GET", f"/polls?id={get_internal2['id']}")).json()[0]["votes"]))
        self.assertIsNone(self.assertQuery(("GET", f"/polls?id={get_internal2['id']}")).json()[0]["accepted"])
        self.assertTrue(self.assertQuery(("GET", f"/polls?id={get_internal2['id']}")).json()[0]["active"])
        self.assertEvent("poll_updated")
        self.assertTrue(self.assertQuery(("GET", f"/users?id={user5}")).json()[0]["external"])
        self.assertQuery(
            ("POST", "/polls/vote"), 200,
            json={"user": user2, "ballot_id": get_internal2["id"], "vote": True}
        )
        self.assertTrue(self.assertQuery(("GET", f"/polls?id={get_internal2['id']}")).json()[0]["accepted"])
        self.assertFalse(self.assertQuery(("GET", f"/polls?id={get_internal2['id']}")).json()[0]["active"])
        self.assertEvent("poll_updated")
        self.assertEvent("poll_closed", ["id", "user", "accepted", "aborted", "variant", "last_vote"])
        self.assertFalse(self.assertQuery(("GET", f"/users?id={user6}")).json()[0]["external"])
        self.assertIsNone(self.assertQuery(("GET", f"/users?id={user6}")).json()[0]["voucher_id"])

        # Check that two votes against a poll close them without accepting
        self.assertFalse(self.assertQuery(("GET", f"/users?id={user4}")).json()[0]["external"])
        self.assertEqual(0, len(self.assertQuery(("GET", f"/polls?id={loose_internal['id']}")).json()[0]["votes"]))
        self.assertQuery(
            ("POST", "/polls/vote"), 200,
            json={"user": alias1, "ballot_id": loose_internal["id"], "vote": False}
        )
        self.assertEqual(1, len(self.assertQuery(("GET", f"/polls?id={loose_internal['id']}")).json()[0]["votes"]))
        self.assertIsNone(self.assertQuery(("GET", f"/polls?id={loose_internal['id']}")).json()[0]["accepted"])
        self.assertTrue(self.assertQuery(("GET", f"/polls?id={loose_internal['id']}")).json()[0]["active"])
        self.assertEvent("poll_updated")
        loose_internal_poll_vote = self.assertQuery(
            ("POST", "/polls/vote"), 200,
            json={"user": user2, "ballot_id": loose_internal["id"], "vote": False}
        ).json()
        self.assertEqual(loose_internal["id"], loose_internal_poll_vote["poll"]["id"])
        self.assertEqual(user4, loose_internal_poll_vote["poll"]["user"]["id"])
        self.assertEqual(user2, loose_internal_poll_vote["poll"]["creator_id"])
        self.assertFalse(self.assertQuery(("GET", f"/polls?id={loose_internal['id']}")).json()[0]["accepted"])
        self.assertFalse(self.assertQuery(("GET", f"/polls?id={loose_internal['id']}")).json()[0]["active"])
        self.assertFalse(self.assertQuery(("GET", f"/users?id={user4}")).json()[0]["external"])
        self.assertEvent("poll_updated")
        self.assertEvent(
            "poll_closed",
            {
                "id": loose_internal["id"],
                "user": user4,
                "accepted": False,
                "aborted": False,
                "variant": "loose_internal",
                "last_vote": loose_internal_poll_vote["vote"]["id"]
            }
        )

        # Check that aborting a poll is possible only for the creator user
        for issuer in [user1, alias1, user7, alias3, user5, alias2]:
            self.assertQuery(
                ("POST", "/polls/abort"), 400,
                json={"id": loose_permission["id"], "issuer": issuer}
            )
        poll_loose_permission = self.assertQuery(
            ("POST", "/polls/abort"), 200,
            json={"id": loose_permission["id"], "issuer": user2}
        ).json()
        self.assertQuery(
            ("POST", "/polls/abort"), 400,
            json={"id": loose_permission["id"], "issuer": user2}
        )
        self.assertFalse(poll_loose_permission["accepted"])
        self.assertFalse(poll_loose_permission["active"])
        self.assertEvent("poll_closed", {"id": loose_permission["id"], "aborted": True, "accepted": False})

    def test_no_duplicate_polls(self):
        self.login()
        self.assertListEqual([], self.assertQuery(("GET", "/polls"), 200).json())
        self.assertQuery(("POST", "/callbacks"), 201, json={"url": f"http://localhost:{self.callback_server_port}/"})

        with self.get_db_session() as session:
            user1_model = models.User(name="user1", external=False, permission=True)
            user2_model = models.User(name="user2", external=False, permission=True)
            session.add_all([user1_model, user2_model])
            session.commit()

            self.assertQuery(
                ("POST", "/polls"), 201,
                json={"user": user1_model.id, "issuer": user2_model.id, "variant": "loose_internal"}
            )
            self.assertEvent("poll_created", ["id", "user", "variant"])
            self.assertQuery(
                ("POST", "/polls"), 400,
                json={"user": user1_model.id, "issuer": user2_model.id, "variant": "loose_internal"}
            ).json()

    def test_communisms(self):
        self.login()
        self.assertListEqual([], self.assertQuery(("GET", "/communisms"), 200).json())

        # Adding the callback server for testing
        self.assertQuery(("POST", "/callbacks"), 201, json={"url": f"http://localhost:{self.callback_server_port}/"})

        # The user mentioned in the 'creator' field is not found
        self.assertQuery(
            ("POST", "/communisms"),
            400,
            json={
                "amount": 1337,
                "description": "description4",
                "creator": 42
            }
        )
        user1 = self.assertQuery(("POST", "/users"), 201, json={"name": "foo"}, r_schema=_schemas.User).json()

        # Fail due to restricted user account
        self.assertQuery(
            ("POST", "/communisms"),
            400,
            json={
                "amount": 1,
                "description": "description1",
                "creator": user1["id"]
            }
        )

        # Allow the user to create communisms
        self._edit_user(user1["id"], permission=True, external=False)

        # Create and get the first communism object
        communism1 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 1,
                "description": "description1",
                "creator": user1["id"]
            },
            r_schema=_schemas.Communism
        ).json()
        self.assertListEqual([communism1], self.assertQuery(("GET", "/communisms?id=1"), 200).json())
        self.assertEvent("communism_created", {"id": 1, "amount": 1, "user": user1["id"], "participants": 1})

        # User referenced by participant 3 doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/communisms"),
            400,
            json={"amount": 42, "description": "description2", "creator": 3}
        ).json()
        user2 = self.assertQuery(("POST", "/users"), 201, json={"name": "bar"}, r_schema=_schemas.User).json()

        # Create and get the second communism object
        response2 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 42,
                "description": "description2",
                "creator": user1["id"]
            },
            r_schema=_schemas.Communism
        )
        communism2 = response2.json()
        self.assertListEqual([communism2], self.assertQuery(("GET", "/communisms?id=2"), 200).json())
        self.assertEvent("communism_created", {"id": 2, "amount": 42, "user": user1["id"], "participants": 1})

        # Allow the user 2 to create communisms by vouching
        self.assertQuery(
            ("POST", "/users/setVoucher"),
            200,
            json={"debtor": user2["id"], "voucher": user1["id"], "issuer": user1["id"]}
        )
        self.assertEvent("voucher_updated")

        # Create and get the third communism object
        response3 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 1337,
                "description": "description3",
                "creator": user2["id"]
            },
            r_schema=_schemas.Communism
        )
        communism3 = response3.json()
        self.assertListEqual([communism3], self.assertQuery(("GET", "/communisms?id=3"), 200).json())
        self.assertEvent("communism_created", {"id": 3, "amount": 1337, "user": user2["id"], "participants": 1})

        # Add new users to the third communism
        for i in range(22):
            communism3_changed = self.assertQuery(
                ("POST", "/communisms/increaseParticipation"),
                200,
                json={"id": 3, "user": user1["id"]},
                r_schema=_schemas.Communism
            ).json()
            self.assertListEqual([communism3_changed], self.assertQuery(("GET", "/communisms?id=3"), 200).json())
        for i in range(22):
            self.assertEvent("communism_updated", {"id": 3, "participants": 2 + i})

        # Remove a user from the third communism
        communism3_changed = self.assertQuery(
            ("POST", "/communisms/decreaseParticipation"),
            200,
            json={"id": 3, "user": user1["id"]},
            r_schema=_schemas.Communism
        ).json()
        self.assertListEqual([communism3_changed], self.assertQuery(("GET", "/communisms?id=3"), 200).json())
        self.assertEqual(len(communism3_changed["participants"]), 2)
        self.assertEqual(communism3_changed["participants"][1]["quantity"], 21)
        self.assertEvent("communism_updated", {"id": 3, "participants": 22})

        # Modify the quantity of a user from the third communism
        communism3_changed = self.assertQuery(
            ("POST", "/communisms/increaseParticipation"),
            200,
            json={"id": 3, "user": user1["id"]},
            r_schema=_schemas.Communism
        ).json()
        query = "/communisms?active=true&unique_participants=2"
        self.assertListEqual([communism3_changed], self.assertQuery(("GET", query), 200).json())
        self.assertEqual(len(communism3_changed["participants"]), 2)
        self.assertEqual(communism3_changed["participants"][1]["quantity"], 22)
        self.assertEvent("communism_updated", {"id": 3, "participants": 23})

        # The newly added participant doesn't exist
        self.assertQuery(("POST", "/communisms/increaseParticipation"), 400, json={"id": 3, "user": 42})

        # Do not allow to delete communisms
        self.assertQuery(
            ("DELETE", "/communisms"),
            [400, 404, 405]
        )
        self.assertQuery(
            ("DELETE", "/communisms/1"),
            [400, 404, 405]
        )

        # Add another new user to the communism
        user3_id = self.assertQuery(("POST", "/users"), 201, json={"name": "baz"}, r_schema=_schemas.User).json()["id"]
        self.assertQuery(
            ("POST", "/users/setVoucher"),
            200,
            json={"debtor": user3_id, "voucher": user1["id"], "issuer": user1["id"]},
            r_schema=_schemas.VoucherUpdateResponse
        )
        self.assertEvent("voucher_updated", {"id": user3_id, "voucher": user1["id"]})
        self.assertQuery(
            ("POST", "/communisms/decreaseParticipation"),
            400,
            json={"id": 3, "user": user3_id}
        ).json()
        self.assertQuery(
            ("POST", "/communisms/increaseParticipation"),
            200,
            json={"id": 3, "user": user3_id},
            r_schema=_schemas.Communism
        ).json()
        self.assertEvent("communism_updated", {"id": 3, "participants": 24})

        # Do not allow another user to close the communism
        self.assertQuery(
            ("POST", "/communisms/close"),
            400,
            json={"id": 3, "issuer": 1}
        )
        self.assertQuery(
            ("POST", "/communisms/close"),
            400,
            json={"id": 3, "issuer": user1["id"]}
        )
        self.assertQuery(
            ("POST", "/communisms/close"),
            400,
            json={"id": 3, "issuer": 10}
        )

        # Close the third communism and expect all balances to be adjusted (creator is participant!)
        users = self.assertQuery(("GET", "/users?community=false"), 200).json()
        self.assertEqual(self.assertQuery(("GET", "/transactions"), 200).json(), [])
        communism3_changed = self.assertQuery(
            ("POST", "/communisms/close"),
            200,
            json={"id": 3, "issuer": user2["id"]},
            r_schema=_schemas.Communism
        ).json()
        self.assertFalse(communism3_changed["active"])
        self.assertIsNotNone(communism3_changed["modified"])
        self.assertIsNotNone(communism3_changed["created"])
        self.assertEvent("communism_closed", {"id": 3, "transactions": 2, "aborted": False, "participants": 24})
        users_updated = self.assertQuery(("GET", "/users?community=false"), 200).json()
        transactions = self.assertQuery(("GET", "/transactions"), 200).json()
        for t in transactions:
            del t["timestamp"]
        user1, user2, user3 = users_updated
        self.assertListEqual(transactions, [
            {
                "id": 1,
                "sender": user1,
                "receiver": user2,
                "amount": 1232,
                "reason": "communism[1]: description3",
                "multi_transaction_id": 1
            },
            {
                "id": 2,
                "sender": user3,
                "receiver": user2,
                "amount": 56,
                "reason": "communism[2]: description3",
                "multi_transaction_id": 1
            }
        ])
        self.assertEvent("transaction_created", {"id": 1, "amount": 1232})
        self.assertEvent("transaction_created", {"id": 2, "amount": 56, "sender": user3["id"], "receiver": user2["id"]})

        # Check that the multi transaction worked as expected
        self.assertEqual(users[0]["balance"] - 1232, users_updated[0]["balance"])
        self.assertEqual(users[1]["balance"] + 1288, users_updated[1]["balance"])
        self.assertEqual(users[2]["balance"] - 56, users_updated[2]["balance"])

        # Updating a communism that doesn't exist or that is already closed shouldn't work
        self.assertListEqual([], self.assertQuery(("GET", "/communisms?id=4"), 200).json())
        self.assertQuery(
            ("POST", "/communisms/increaseParticipation"),
            400,
            json={"id": 4, "user": 3}
        ).json()
        self.assertQuery(
            ("POST", "/communisms/decreaseParticipation"),
            400,
            json={"id": 4, "user": 2}
        ).json()
        self.assertListEqual([communism3_changed], self.assertQuery(("GET", "/communisms?active=false"), 200).json())

        # Check that a multi transaction has been created by closing the communism
        time.sleep(0.1)
        with self.get_db_session() as session:
            self.assertEqual(1, len(session.query(models.MultiTransaction).all()))
            self.assertEqual(56, session.query(models.MultiTransaction).get(1).base_amount)

    def test_communism_schema_checks(self):
        self.login()
        sample_data = [
            {},
            {
                "amount": 0,
                "description": "description",
                "creator": 1
            },
            {
                "amount": -42,
                "description": "description",
                "creator": 1
            },
            {
                "amount": 1,
                "description": "description",
                "creator": -4
            },
            {
                "amount": 1,
                "creator": 1
            },
            {
                "amount": 1,
                "description": "description"
            }
        ]

        for entry in sample_data:
            self.assertQuery(
                ("POST", "/communisms"),
                400,
                json=entry
            )

    def test_balance_limits(self):
        self.login()
        user1 = self.assertQuery(("POST", "/users"), 201, json={"name": "user1"}, r_schema=_schemas.User).json()
        user2 = self.assertQuery(("POST", "/users"), 201, json={"name": "user2"}, r_schema=_schemas.User).json()

        self._edit_user(user1["id"], permission=True, external=False)
        self._edit_user(user2["id"], permission=True, external=False)
        self.assertQuery(("POST", "/transactions/send"), 201, json={
            "sender": user1["id"],
            "receiver": user2["id"],
            "amount": 50000,
            "reason": "test"
        })
        self.assertQuery(("POST", "/transactions/send"), 400, json={
            "sender": user1["id"],
            "receiver": user2["id"],
            "amount": 50001,
            "reason": "test"
        })

        self._edit_user(user1["id"], balance=0)
        self._edit_user(user2["id"], balance=2**31 - 10)
        self.assertQuery(("POST", "/transactions/send"), 201, json={
            "sender": user1["id"],
            "receiver": user2["id"],
            "amount": 8,
            "reason": "test"
        })
        self.assertQuery(("POST", "/transactions/send"), 400, json={
            "sender": user1["id"],
            "receiver": user2["id"],
            "amount": 1,
            "reason": "test"
        })

        self._edit_user(user1["id"], balance=-2**31 + 10)
        self._edit_user(user2["id"], balance=0)
        self.assertQuery(("POST", "/transactions/send"), 201, json={
            "sender": user1["id"],
            "receiver": user2["id"],
            "amount": 9,
            "reason": "test"
        })
        self.assertQuery(("POST", "/transactions/send"), 400, json={
            "sender": user1["id"],
            "receiver": user2["id"],
            "amount": 1,
            "reason": "test"
        })

    def test_callbacks(self):
        self.assertEqual(0, self.callback_event_queue.qsize())
        self.assertQuery(
            ("POST", "/callbacks"),
            401,
            json={"url": f"http://localhost:{self.callback_server_port}/"}
        )
        self.login()
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"url": f"http://localhost:{self.callback_server_port}/"}
        )
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"url": "http://localhost:64000"}
        )
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"url": "http://localhost:65000", "app": 1}
        )


class UninitializedAPITests(utils.BaseAPITests):
    EXTRA_API_SERVER_ENV_VARS = {"SKIP_INITIALIZATION": "yes"}

    def test_special_user(self):
        self.login()
        self.assertEqual([], self.assertQuery(("GET", "/users"), 200).json())
        self.assertEqual([], self.assertQuery(("GET", "/users?community=y"), 200).json())
        self.make_special_user()
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=1"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=TRUE"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=true"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=y"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/users"), 200).json()))
        self.make_special_user()
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=1"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=TRUE"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=true"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/users?community=y"), 200).json()))
        self.assertEqual(1, len(self.assertQuery(("GET", "/users"), 200).json()))

    def test_user_search(self):
        self.login()

        def comp(x: int, query: str):
            data = self.assertQuery(("GET", "/users" + (query and "?" + query)), 200).json()
            self.assertEqual(x, len(data), str(data))

        session = self.get_db_session()
        comp(0, "")

        session.add(models.User(name="user1", active=False, external=False, permission=False))
        session.commit()
        comp(1, "")

        session.add(models.User(name="user2", active=True, external=True))
        session.commit()
        comp(2, "")

        session.add(models.User(name="user3", active=True, external=False, permission=True))
        session.add(models.User(name="user4", active=True, external=False, permission=True))
        session.commit()
        comp(4, "")

        session.add(models.User(name="user5", external=False))
        session.commit()
        comp(5, "")

        session.add(models.User(name="user6", active=False, external=False))
        session.commit()
        comp(6, "")

        session.add(models.User(name="user7", external=True, permission=False, voucher_id=3))
        session.commit()
        comp(7, "")

        comp(1, "id=1")
        comp(1, "id=2")
        comp(1, "id=3")

        comp(0, "name=foo")
        comp(0, "name=user")
        comp(1, "name=user3")
        comp(1, "name=user6")
        comp(0, "name=user10")
        comp(1, "active=true&name=user5")
        comp(0, "active=false&name=user5")
        comp(0, "active=true&name=user6")

        comp(5, "active=true")
        comp(2, "active=false")

        comp(2, "external=true")
        comp(5, "external=false")

        comp(2, "active=true&external=false&permission=true")

        comp(1, "voucher_id=3")
        comp(0, "voucher_id=4")
        comp(0, "voucher_id=3&active=false")

        comp(5, "external=false")
        comp(3, "external=false&active=true")
        comp(2, "external=false&active=false")

        session.add(models.Application(name="app", password="password", salt="salt"))
        session.commit()

        session.add(models.Alias(user_id=3, application_id=1, username="foo"))
        session.add(models.Alias(user_id=3, application_id=1, username="bar"))
        session.add(models.Alias(user_id=4, application_id=1, username="baz", confirmed=True))
        session.add(models.Alias(user_id=5, application_id=1, username="foobar", confirmed=True))
        session.commit()

        comp(7, "")
        comp(1, "alias_id=1")
        comp(1, "alias_id=2")
        comp(0, "alias_application=foo")
        comp(0, "alias_application=app")
        comp(3, "alias_application=application")
        comp(3, "alias_application_id=1")
        comp(0, "alias_application_id=2")
        comp(1, "alias_confirmed=false")
        comp(2, "alias_confirmed=true")
        comp(1, "alias_confirmed=true&alias_username=baz")
        comp(0, "alias_confirmed=true&alias_username=baz&id=1")

        session.close()


if __name__ == '__main__':
    _unittest.main()
