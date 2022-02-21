"""
MateBot unit tests for the whole API in certain user actions
"""

import time
import unittest as _unittest
from typing import Type

import requests

from matebot_core import schemas as _schemas

from . import utils


api_suite = _unittest.TestSuite()


def _tested(cls: Type):
    global api_suite
    for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
        api_suite.addTest(cls(fixture))
    return cls


@_tested
class UninitializedAPITests(utils.BaseAPITests):
    def _init_project_data(self):
        pass


@_tested
class WorkingAPITests(utils.BaseAPITests):
    def setUp(self) -> None:
        super().setUp()
        self.login()

    def _set_user_attrs(self, uid: int, success: bool, applied: bool, **kwargs) -> dict:
        user = self.assertQuery(("GET", f"/users/{uid}"), 200).json()
        user.update(**kwargs)
        new_user = self.assertQuery(
            ("PUT", "/users"),
            200 if success else [400, 403, 404, 409],
            json=user,
            r_schema=_schemas.User if success else None,
            recent_callbacks=[("GET", f"/update/user/{uid}")] if success else None
        ).json()
        if applied:
            for k, v in kwargs.items():
                self.assertEqual(new_user[k], v)
        return new_user

    def test_basic_endpoints_and_redirects_to_docs(self):
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

    def test_special_user(self):
        self.assertEqual([], self.assertQuery(("GET", "/users"), 200).json())
        self.assertQuery(("GET", "/users/community"), 500)
        self.make_special_user()
        self.assertQuery(("GET", "/users/community"), 200)
        self.assertEqual(1, len(self.assertQuery(("GET", "/users"), 200).json()))
        self.make_special_user()
        self.assertQuery(("GET", "/users/community"), 200)
        self.assertEqual(1, len(self.assertQuery(("GET", "/users"), 200).json()))

    def test_users(self):
        self.assertListEqual([], self.assertQuery(("GET", "/users"), 200).json())

        # Creating a set of test users
        users = []
        for i in range(10):
            user = self.assertQuery(
                ("POST", "/users"),
                201,
                json={"name": f"user{i+1}", "permission": True, "external": False},
                r_schema=_schemas.User
            ).json()
            self.assertEqual(i+1, user["id"])
            self.assertEqual(
                user,
                self.assertQuery(("GET", f"/users/{i+1}"), 200, r_schema=_schemas.User).json()
            )
            users.append(user)
            self.assertEqual(
                users,
                self.assertQuery(("GET", "/users"), 200).json()
            )

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/create/callback/1")]
        )
        time.sleep(1)

        for u in users:
            self._set_user_attrs(u["id"], True, True)

        # Deleting users should not work by 'DELETE' but with disabling via 'POST'
        self.assertQuery(
            ("DELETE", "/users"),
            [405, 409],
            json=users[-1]
        )
        j = len(users) - 1
        self.assertQuery(
            ("POST", f"/users/disable/{j}"),
            200,
            r_schema=_schemas.User,
            recent_callbacks=[("GET", f"/update/user/{j}")]
        )
        users.pop()

        user0 = users[0]
        user1 = users[1]
        user2 = users[2]

        # Updating the balance, special flag, access times or aliases of a user should fail
        self._set_user_attrs(user1["id"], True, False, balance=0)
        self._set_user_attrs(user1["id"], True, False, balance=1)
        self._set_user_attrs(user1["id"], True, False, created=1337)
        self._set_user_attrs(user1["id"], True, False, modified=42)
        self._set_user_attrs(user1["id"], True, False, aliases=[{
            "id": 1,
            "user_id": user1["id"],
            "application_id": 1,
            "app_username": "unknown@none",
            "confirmed": True
        }])
        self._set_user_attrs(user1["id"], True, True)
        self.assertEqual(user1, self.assertQuery(("GET", f"/users/{user1['id']}"), 200).json())

        # Updating the name, and permission external flags should work, everything else is ignored
        self._set_user_attrs(user1["id"], False, False, external=True)
        self._set_user_attrs(user1["id"], True, True, permission=False)
        self._set_user_attrs(user1["id"], True, True, external=True)
        self._set_user_attrs(user1["id"], True, False, voucher_id=user0["id"])
        self._set_user_attrs(user1["id"], True, False, active=True)
        self._set_user_attrs(user1["id"], True, False, voucher_id=None)
        self._set_user_attrs(user1["id"], True, False, active=False)
        self._set_user_attrs(user1["id"], True, False, active=True)
        user1_new = user1.copy()
        user1_remote = self.assertQuery(("GET", f"/users/{user1['id']}"), 200).json()
        user1_new.update(permission=False, external=True, modified=user1_remote["modified"])
        self.assertEqual(user1_new, user1_remote)

        # Transactions from/to disabled users should fail
        self.assertQuery(
            ("POST", "/transactions"),
            400,
            json={
                "sender_id": user1["id"],
                "receiver_id": user2["id"],
                "amount": 42,
                "reason": "test"
            }
        )
        self.assertQuery(
            ("POST", "/transactions"),
            400,
            json={
                "sender_id": user2["id"],
                "receiver_id": user1["id"],
                "amount": 42,
                "reason": "test"
            }
        )

        # Deleting users with balance != 0 should fail
        self.assertEqual(0, self.assertQuery(("GET", f"/users/{user0['id']}"), 200).json()["balance"])
        self.assertEqual(0, self.assertQuery(("GET", f"/users/{user2['id']}"), 200).json()["balance"])
        self.assertQuery(
            ("POST", "/transactions"),
            201,
            json={
                "sender_id": user0["id"],
                "receiver_id": user2["id"],
                "amount": 42,
                "reason": "test"
            },
            recent_callbacks=[("GET", "/create/transaction/1")]
        )
        user0 = self.assertQuery(("GET", f"/users/{user0['id']}"), 200).json()
        user2 = self.assertQuery(("GET", f"/users/{user2['id']}"), 200).json()
        self.assertEqual(user0["balance"], -user2["balance"])
        self.assertQuery(("POST", f"/users/disable/{user0['id']}"), 400)

        # Deleting the user after fixing the balance should work again
        self.assertQuery(
            ("POST", "/transactions"),
            201,
            json={
                "sender_id": user2["id"],
                "receiver_id": user0["id"],
                "amount": 42,
                "reason": "reverse"
            },
            skip_callbacks=2,
            recent_callbacks=[("GET", "/create/transaction/2")]
        )
        user0 = self.assertQuery(("GET", f"/users/{user0['id']}"), 200).json()
        user2 = self.assertQuery(("GET", f"/users/{user2['id']}"), 200).json()
        self.assertEqual(user0["balance"], 0)
        self.assertEqual(user2["balance"], 0)
        self.assertQuery(
            ("POST", f"/users/disable/{user0['id']}"),
            200,
            recent_callbacks=[("GET", f"/update/user/{user0['id']}")]
        )
        self.assertQuery(
            ("POST", f"/users/disable/{user2['id']}"),
            200,
            recent_callbacks=[("GET", f"/update/user/{user2['id']}")]
        )
        users.pop(0)
        users.pop(0)
        users.pop(0)

        # Deleting users that created/participate in an active communism shouldn't work
        user0 = users[0]
        user1 = users[1]
        communism = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 1337,
                "description": "description",
                "creator_id": user0["id"],
                "active": True,
                "participants": [{"quantity": 1, "user_id": user1["id"]}]
            },
            recent_callbacks=[("GET", "/create/communism/1")]
        ).json()
        self.assertQuery(("POST", f"/users/disable/{user0['id']}"), 400)
        self.assertQuery(("POST", f"/users/disable/{user1['id']}"), 400)
        self.assertEqual(communism, self.assertQuery(("GET", "/communisms/1"), 200).json())

        # Deleting users that don't participate in active communisms should work
        self.assertQuery(
            ("POST", "/communisms/setParticipants/1"),
            200,
            json=[],
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/update/communism/1")]
        )
        self.assertQuery(
            ("POST", f"/users/disable/{user1['id']}"),
            200,
            recent_callbacks=[("GET", f"/update/user/{user1['id']}")]
        )
        self.assertQuery(
            ("POST", "/communisms/abort/1"),
            200,
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/update/communism/1")]
        )
        self.assertQuery(
            ("POST", f"/users/disable/{user0['id']}"),
            200,
            recent_callbacks=[("GET", f"/update/user/{user0['id']}")]
        )
        users.pop(0)
        users.pop(1)

        self.assertEqual(len(self.assertQuery(("GET", "/users"), 200).json()), 10, "Might I miss something?")

    def test_refunds(self):
        self.make_special_user()
        community = self.assertQuery(("GET", "/users/community"), 200).json()
        self.assertListEqual([], self.assertQuery(("GET", "/refunds"), 200).json())
        self.assertEqual(len(self.assertQuery(("GET", "/votes"), 200).json()), 0)

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/create/callback/1")]
        )

        # Adding the creator user
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user1", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/2")]
        ).json()

        # Create the first refund request
        refund1 = self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Do you like this?", "amount": 42, "creator_id": 2},
            r_schema=_schemas.Refund,
            recent_callbacks=[("GET", "/create/refund/1")]
        ).json()
        self.assertEqual(refund1["id"], 1)
        self.assertEqual(refund1["active"], True)
        self.assertEqual(refund1["ballot_id"], 1)
        self.assertEqual(refund1["votes"], [])

        # Add another refund request to be sure
        refund2 = self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Are you sure?", "amount": 1337, "creator_id": 2},
            recent_callbacks=[("GET", "/create/refund/2")]
        ).json()
        self.assertEqual(refund2["id"], 2)
        self.assertEqual(refund2["votes"], [])
        self.assertEqual(refund2["allowed"], None)
        self.assertEqual(refund2["transaction"], None)
        self.assertEqual(refund2["active"], True)

        # Abort the second refund request
        refund2 = self.assertQuery(
            ("POST", "/refunds/abort/2"),
            200,
            recent_callbacks=[("GET", "/update/refund/2")]
        ).json()
        self.assertEqual(refund2["allowed"], False)
        self.assertEqual(refund2["transaction"], None)
        self.assertEqual(refund2["active"], False)

        # A user can't vote on its own refund requests
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user_id": 2, "ballot_id": 1, "vote": True}
        )

        # Adding an unprivileged user
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user2", "permission": False, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/3")]
        ).json()
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user_id": 3, "ballot_id": 1, "vote": True}
        )

        # Adding a privileged user which gets disabled first, though
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user3", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/4")]
        ).json()
        self.assertQuery(("POST", "/users/disable/4"), 200, recent_callbacks=[("GET", "/update/user/4")])
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user_id": 4, "ballot_id": 1, "vote": True}
        )

        # Adding a new user to actually vote on the refund for the first time
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user4", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/5")]
        ).json()
        vote1 = self.assertQuery(
            ("POST", "/refunds/vote"),
            200,
            json={"user_id": 5, "ballot_id": 1, "vote": True},
            r_schema=_schemas.RefundVoteResponse,
            recent_callbacks=[("GET", "/create/vote/1")]
        ).json()
        self.assertEqual(vote1["vote"]["vote"], True)
        self.assertEqual(vote1["vote"]["ballot_id"], 1)
        self.assertIsNone(vote1["refund"]["transaction"])
        self.assertGreaterEqual(vote1["refund"]["modified"], refund1["created"])
        self.assertListEqual(vote1["refund"]["votes"], [vote1["vote"]])

        # The community user shouldn't vote on refund requests
        self.assertQuery(
            ("POST", "/refunds/vote"),
            [400, 409],
            json={"user_id": community["id"], "ballot_id": 1, "vote": True}
        )

        # Add another user to accept the refund request
        old_balance = self.assertQuery(("GET", "/users/2"), 200).json()["balance"]
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user5", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/6")]
        )
        vote2 = self.assertQuery(
            ("POST", "/refunds/vote"),
            200,
            json={"user_id": 6, "ballot_id": 1, "vote": True},
            r_schema=_schemas.RefundVoteResponse,
            recent_callbacks=[("GET", "/create/vote/2"), ("GET", "/create/transaction/1"), ("GET", "/update/refund/1")]
        ).json()
        self.assertListEqual(vote2["refund"]["votes"], [vote1["vote"], vote2["vote"]])
        self.assertIsNotNone(vote2["refund"]["transaction"])
        transaction = _schemas.Transaction(**vote2["refund"]["transaction"])
        self.assertEqual(transaction.amount, 42)
        self.assertEqual(transaction.sender.id, 1)
        self.assertEqual(transaction.receiver.id, 2)
        self.assertIsNone(transaction.multi_transaction_id)
        self.assertEqual(vote2["refund"]["allowed"], True)
        self.assertEqual(vote2["refund"]["active"], False)

        new_balance = self.assertQuery(("GET", "/users/2"), 200).json()["balance"]
        self.assertGreater(new_balance, old_balance)
        self.assertEqual(new_balance, old_balance + 42)
        transactions = self.assertQuery(("GET", "/transactions"), 200).json()
        self.assertListEqual([transaction], transactions)

        # Don't allow to add votes to already closed refund requests
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user6", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/7")]
        )
        self.assertQuery(("POST", "/refunds/vote"), 400, json={"user_id": 7, "ballot_id": 1, "vote": True})

        # The community user shouldn't create refunds
        self.assertQuery(
            ("POST", "/refunds"),
            409,
            json={"description": "Foo", "amount": 1337, "creator_id": community["id"]}
        )

        # User referenced by 'creator' doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/refunds"),
            404,
            json={"description": "Foo", "amount": 1337, "creator_id": 8}
        ).json()
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user7", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/8")]
        ).json()
        self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Foo", "amount": 1337, "creator_id": 8}
        ).json()

        # Don't send votes for memberships polls to the refund endpoint
        # TODO

    def test_communisms(self):
        self.assertListEqual([], self.assertQuery(("GET", "/communisms"), 200).json())

        # Creating some working sample data for the unit test
        sample_data = [
            {
                "amount": 1,
                "description": "description1",
                "creator_id": None,  # will be inserted later
                "active": True,
                "participants": []
            },
            {
                "amount": 42,
                "description": "description2",
                "creator_id": None,  # will be inserted later
                "active": True,
                "participants": [
                    {
                        "user_id": 1,
                        "quantity": 1
                    },
                    {
                        "user_id": 2,
                        "quantity": 2
                    }
                ]
            },
            {
                "amount": 1337,
                "description": "description3",
                "creator_id": None  # will be inserted later
            },
            {
                "amount": 1337,
                "description": "description4",
                "creator_id": 42
            },
        ]

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/create/callback/1")]
        )

        # The user mentioned in the 'creator_id' field is not found
        self.assertQuery(
            ("POST", "/communisms"),
            404,
            json=sample_data[3]
        )
        user1 = self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user1", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/1")]
        ).json()
        sample_data[0]["creator_id"] = user1["id"]
        sample_data[1]["creator_id"] = user1["id"]

        # Create and get the first communism object
        communism1 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json=sample_data[0],
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/create/communism/1")]
        ).json()
        self.assertQuery(
            ("GET", "/communisms/1"),
            200,
            r_schema=_schemas.Communism(**communism1)
        ).json()

        # User referenced by participant 2 doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/communisms"),
            404,
            json=sample_data[1]
        ).json()
        user2 = self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user2", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/2")]
        ).json()
        sample_data[2]["creator_id"] = user2["id"]

        # Create and get the second communism object
        response2 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json=sample_data[1],
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/create/communism/2")]
        )
        communism2 = response2.json()
        self.assertQuery(
            ("GET", "/communisms/2"),
            200,
            r_schema=_schemas.Communism(**communism2)
        ).json()
        self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism2,
            r_schema=_schemas.Communism(**communism2),
            recent_callbacks=[("GET", "/update/communism/2")]
        ).json()

        # Create and get the third communism object
        response3 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json=sample_data[2],
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/create/communism/3")]
        )
        communism3 = response3.json()
        self.assertQuery(
            ("GET", "/communisms/3"),
            200,
            r_schema=_schemas.Communism(**communism3)
        ).json()

        # Perform a PUT operation with the same data (that shouldn't change anything)
        self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism2,
            r_schema=communism2,
            recent_callbacks=[("GET", "/update/communism/2")]
        )

        # Add new users to the third communism
        communism3["participants"] = [
            _schemas.CommunismUserBinding(user_id=1, quantity=10).dict(),
            _schemas.CommunismUserBinding(user_id=2, quantity=20).dict()
        ]
        response3_changed = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/update/communism/3")]
        )
        communism3_changed = response3_changed.json()
        self.assertEqual(communism3_changed, communism3)
        self.assertQuery(
            ("GET", "/communisms/3"),
            200,
            r_schema=communism3_changed
        )

        # Remove a user from the third communism
        communism3["participants"] = [
            _schemas.CommunismUserBinding(user_id=1, quantity=10).dict()
        ]
        communism3_changed = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/update/communism/3")]
        ).json()
        self.assertEqual(communism3_changed, communism3)
        self.assertQuery(
            ("GET", "/communisms/3"),
            200,
            r_schema=communism3_changed
        )

        # Modify the quantity of a user from the third communism
        communism3["participants"] = [
            _schemas.CommunismUserBinding(user_id=1, quantity=40).dict()
        ]
        communism3 = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism(**communism3),
            recent_callbacks=[("GET", "/update/communism/3")]
        ).json()

        # Add and modify users from the third communism
        communism3["participants"] = [
            _schemas.CommunismUserBinding(user_id=1, quantity=10).dict(),
            _schemas.CommunismUserBinding(user_id=2, quantity=3).dict(),
            _schemas.CommunismUserBinding(user_id=3, quantity=7).dict()
        ]
        self.assertQuery(
            ("PUT", "/communisms"),
            404,
            json=communism3
        ).json()
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user3", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/3")]
        )
        communism3 = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism(**communism3),
            r_schema_ignored_fields=["modified", "created"],
            recent_callbacks=[("GET", "/update/communism/3")]
        ).json()

        # Do not allow to delete communisms
        self.assertQuery(
            ("DELETE", "/communisms"),
            [400, 404, 405]
        )
        self.assertQuery(
            ("DELETE", "/communisms/1"),
            [400, 404, 405]
        )

        # Forbid to update a communism if a user is mentioned twice or more
        communism3_broken = communism3.copy()
        communism3_broken["participants"] = [
            {"user_id": 1, "quantity": 10},
            {"user_id": 1, "quantity": 10},
            {"user_id": 1, "quantity": 10},
            {"user_id": 2, "quantity": 20}
        ]
        self.assertQuery(
            ("PUT", "/communisms"),
            409,
            json=communism3_broken
        )

        # Close the third communism and expect all balances to be adjusted (creator is participant!)
        users = self.assertQuery(("GET", "/users"), 200).json()
        self.assertEqual(self.assertQuery(("GET", "/transactions"), 200).json(), [])
        self.assertEqual(self.assertQuery(("GET", "/transactions/multi"), 200).json(), [])
        communism3["active"] = False
        communism3_changed = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism,
            recent_callbacks=[
                ("GET", "/update/communism/3"),
                ("GET", "/create/multitransaction/1")
            ]
        ).json()
        self.assertFalse(communism3_changed["active"])
        self.assertIsNotNone(communism3_changed["modified"])
        self.assertIsNotNone(communism3_changed["created"])
        users_updated = self.assertQuery(("GET", "/users"), 200).json()
        transactions = self.assertQuery(("GET", "/transactions"), 200).json()
        multi_transactions = self.assertQuery(("GET", "/transactions/multi"), 200).json()
        self.assertEqual(2, len(transactions))
        self.assertEqual(1, len(multi_transactions))
        m = multi_transactions[0]
        del m["timestamp"], m["transactions"][0]["timestamp"], m["transactions"][1]["timestamp"]
        user1, user2, user3 = [self.assertQuery(("GET", f"/users/{i+1}")).json() for i in range(3)]
        self.assertEqual(m, {
            "id": 1,
            "base_amount": 67,
            "total_amount": 1139,
            "transactions": [
                {
                    "id": 1,
                    "sender": user1,
                    "receiver": user2,
                    "amount": 670,
                    "reason": "communism[1]: description3",
                    "multi_transaction_id": 1
                },
                {
                    "id": 2,
                    "sender": user3,
                    "receiver": user2,
                    "amount": 469,
                    "reason": "communism[2]: description3",
                    "multi_transaction_id": 1
                }
            ]
        })
        self.assertEqual(users[0]["balance"], users_updated[0]["balance"] + 670)
        self.assertEqual(users[1]["balance"], users_updated[1]["balance"] - 1139)
        self.assertEqual(users[2]["balance"], users_updated[2]["balance"] + 469)

        # Updating a closed communism should yield HTTP 409
        self.assertQuery(
            ("PUT", "/communisms"),
            400,
            json=communism3_changed
        )

        # Updating a communism that doesn't exist shouldn't work
        self.assertQuery(("GET", "/communisms/4"), 404)
        communism4 = communism3.copy()
        communism4["id"] = 4
        self.assertQuery(
            ("PUT", "/communisms"),
            404,
            json=communism4
        )


@_tested
class FailingAPITests(utils.BaseAPITests):
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
                422,
                json=entry
            )


@_tested
class APICallbackTests(utils.BaseAPITests):
    def test_callback_testing(self):
        self.assertEqual(0, self.callback_request_list.qsize())
        requests.get(f"{self.callback_server_uri}test")
        self.assertEqual(("GET", "/test"), self.callback_request_list.get(timeout=1))
        requests.get(f"{self.callback_server_uri}foo")
        requests.get(f"{self.callback_server_uri}bar")
        requests.get(f"{self.callback_server_uri}baz")
        self.assertEqual(("GET", "/foo"), self.callback_request_list.get(timeout=1))
        self.assertEqual(("GET", "/bar"), self.callback_request_list.get(timeout=0))
        self.assertEqual(("GET", "/baz"), self.callback_request_list.get(timeout=0))

        requests.get(f"{self.callback_server_uri}create/poll/7")
        requests.get(f"{self.callback_server_uri}update/user/3")
        requests.get(f"{self.callback_server_uri}delete/vote/1")
        self.assertEqual(("GET", "/create/poll/7"), self.callback_request_list.get(timeout=0.5))
        self.assertEqual(("GET", "/update/user/3"), self.callback_request_list.get(timeout=0))
        self.assertEqual(("GET", "/delete/vote/1"), self.callback_request_list.get(timeout=0))

    def test_callback_helper(self):
        self.assertEqual(0, self.callback_request_list.qsize())
        self.assertQuery(
            ("POST", "/callbacks"),
            401,
            json={"base": f"http://localhost:{self.callback_server_port}/"}
        )
        self.login()
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"}
        )
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": "http://localhost:64000"},
            recent_callbacks=[("GET", "/create/callback/2")],
            skip_callbacks=1,
            skip_callback_timeout=0.2
        )
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": "http://localhost:65000", "app": 1}
        )


if __name__ == '__main__':
    _unittest.main()
