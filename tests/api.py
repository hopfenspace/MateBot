"""
MateBot unit tests for the whole API in certain user actions
"""

import time
import unittest as _unittest
from typing import Type

import requests

from matebot_core import schemas as _schemas
from matebot_core.persistence import models

from . import utils


api_suite = _unittest.TestSuite()


def _tested(cls: Type):
    global api_suite
    for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
        api_suite.addTest(cls(fixture))
    return cls


@_tested
class APITests(utils.BaseAPITests):
    def setUp(self) -> None:
        super().setUp()
        self.login()

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

    def test_users(self):
        self.assertListEqual([], self.assertQuery(("GET", "/users"), 200).json())

        # Creating a set of test users
        users = []
        for i in range(10):
            user = self.assertQuery(
                ("POST", "/users"),
                201,
                json={"name": f"user{i+1}"},
                r_schema=_schemas.User
            ).json()
            self.assertEqual(i+1, user["id"])
            self.assertEqual(
                user,
                self.assertQuery(("GET", f"/users?id={i+1}"), 200).json()[0]
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
            r_schema=_schemas.User,
            recent_callbacks=[("GET", f"/update/user/{j}")]
        )

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
        self.assertQuery(
            ("POST", "/users/setFlags"),
            200,
            json={"user": user0["id"], "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", f"/update/user/{user0['id']}")]
        )
        self.assertQuery(
            ("POST", "/users/setFlags"),
            200,
            json={"user": user2["id"], "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", f"/update/user/{user2['id']}")]
        )
        self.assertQuery(
            ("POST", "/transactions/send"),
            201,
            json={
                "sender": user0["id"],
                "receiver": user2["id"],
                "amount": 42,
                "reason": "test"
            },
            recent_callbacks=[("GET", "/create/transaction/1")]
        )
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
            },
            skip_callbacks=2,
            recent_callbacks=[("GET", "/create/transaction/2")]
        )
        user0 = self.assertQuery(("GET", f"/users?id={user0['id']}"), 200).json()[0]
        user2 = self.assertQuery(("GET", f"/users?id={user2['id']}"), 200).json()[0]
        self.assertEqual(user0["balance"], 0)
        self.assertEqual(user2["balance"], 0)
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user0["id"], "issuer": user0["id"]},
            recent_callbacks=[("GET", f"/update/user/{user0['id']}")]
        )
        self.assertQuery(
            ("POST", "/users/delete"),
            400,
            json={"id": user2["id"]}
        )
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user2["id"], "issuer": user2["id"]},
            recent_callbacks=[("GET", f"/update/user/{user2['id']}")]
        )
        users.pop(0)
        users.pop(0)
        users.pop(0)

        # Deleting users that created/participate in an active communism shouldn't work
        user0 = users[0]
        user1 = users[1]
        self.assertQuery(
            ("POST", "/users/setFlags"),
            200,
            json={"user": user0["id"], "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", f"/update/user/{user0['id']}")]
        )
        communism = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 1337,
                "description": "description",
                "creator": user0["id"],
                "participants": [{"quantity": 1, "user_id": user1["id"]}]
            },
            recent_callbacks=[("GET", "/create/communism/1")]
        ).json()
        self.assertQuery(("POST", "/users/delete"), 400, json={"id": user0['id']})
        self.assertQuery(("POST", "/users/delete"), 400, json={"id": user1["id"]})
        self.assertListEqual([communism], self.assertQuery(("GET", "/communisms"), 200).json())

        # Deleting users that don't participate in active communisms should work
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user1["id"], "issuer": user1["id"]},
            recent_callbacks=[("GET", f"/update/user/{user1['id']}")]
        )
        self.assertQuery(
            ("POST", "/communisms/abort"),
            200,
            json={"id": 1, "issuer": user0["id"]},
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/update/communism/1")]
        )
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": user0["id"], "issuer": user0["id"]},
            recent_callbacks=[("GET", f"/update/user/{user0['id']}")]
        )
        users.pop(0)
        users.pop(1)

        self.assertEqual(len(self.assertQuery(("GET", "/users"), 200).json()), 10, "Might I miss something?")

    def test_refunds(self):
        self.make_special_user()
        community = self.assertQuery(("GET", "/users?community=1"), 200).json()
        self.assertEqual(len(community), 1)
        community = community[0]
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
            json={"name": "user1"},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/2")]
        ).json()

        # Checking for the permission
        self.assertQuery(
            ("POST", "/refunds"),
            400,
            json={"description": "Do you like this?", "amount": 42, "creator": 2}
        )
        self.assertQuery(
            ("POST", "/users/setFlags"),
            200,
            json={"user": 2, "permission": True, "external": False},
            recent_callbacks=[("GET", "/update/user/2")]
        )

        # Create the first refund request
        refund1 = self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Do you like this?", "amount": 42, "creator": 2},
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
            json={"description": "Are you sure?", "amount": 1337, "creator": 2},
            recent_callbacks=[("GET", "/create/refund/2")]
        ).json()
        self.assertEqual(refund2["id"], 2)
        self.assertEqual(refund2["votes"], [])
        self.assertEqual(refund2["allowed"], None)
        self.assertEqual(refund2["transaction"], None)
        self.assertEqual(refund2["active"], True)

        # Abort the second refund request
        self.assertQuery(
            ("POST", "/refunds/abort"),
            400,
            json={"id": 2, "issuer": 1}
        ).json()
        refund2 = self.assertQuery(
            ("POST", "/refunds/abort"),
            200,
            json={"id": 2, "issuer": 2},
            recent_callbacks=[("GET", "/update/refund/2")]
        ).json()
        self.assertEqual(refund2["allowed"], False)
        self.assertEqual(refund2["transaction"], None)
        self.assertEqual(refund2["active"], False)

        # A user can't vote on its own refund requests
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user": 2, "ballot_id": 1, "vote": True}
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
            json={"user": 3, "ballot_id": 1, "vote": True}
        )

        # Adding a privileged user which gets disabled first, though
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user3", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/4")]
        ).json()
        self.assertQuery(
            ("POST", "/users/delete"),
            200,
            json={"id": 4, "issuer": 4},
            recent_callbacks=[("GET", "/update/user/4")]
        )
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user": 4, "ballot_id": 1, "vote": True}
        )

        # Adding a new user to actually vote on the refund for the first time
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user4", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/5")]
        ).json()
        self.assertQuery(
            ("POST", "/refunds/vote"),
            400,
            json={"user": 5, "ballot_id": 1, "vote": True}
        )
        self.assertQuery(
            ("POST", "/users/setFlags"),
            200,
            json={"user": 5, "permission": True, "external": False},
            recent_callbacks=[("GET", "/update/user/5")]
        )
        vote1 = self.assertQuery(
            ("POST", "/refunds/vote"),
            200,
            json={"user": 5, "ballot_id": 1, "vote": True},
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
            json={"user": community["id"], "ballot_id": 1, "vote": True}
        )

        # Add another user to accept the refund request
        old_balance = self.assertQuery(("GET", "/users?id=2"), 200).json()[0]["balance"]
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user5", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/6")]
        )
        self.assertQuery(
            ("POST", "/users/setFlags"),
            200,
            json={"user": 6, "permission": True},
            recent_callbacks=[("GET", "/update/user/6")]
        )
        vote2 = self.assertQuery(
            ("POST", "/refunds/vote"),
            200,
            json={"user": 6, "ballot_id": 1, "vote": True},
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

        new_balance = self.assertQuery(("GET", "/users?id=2"), 200).json()[0]["balance"]
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
            404,
            json={"description": "Foo", "amount": 1337, "creator": 8}
        ).json()
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user7", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/8")]
        ).json()
        self.assertQuery(
            ("POST", "/users/setVoucher"),
            200,
            json={"debtor": 8, "voucher": 2},
            recent_callbacks=[("GET", "/update/user/8")]
        )
        self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Foo", "amount": 1337, "creator": 8}
        ).json()

        # TODO: Don't send votes for memberships polls to the refund endpoint

    def test_communisms(self):
        self.assertListEqual([], self.assertQuery(("GET", "/communisms"), 200).json())

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/create/callback/1")]
        )

        # The user mentioned in the 'creator' field is not found
        self.assertQuery(
            ("POST", "/communisms"),
            404,
            json={
                "amount": 1337,
                "description": "description4",
                "creator": 42
            }
        )
        user1 = self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user1"},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/1")]
        ).json()

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
        self.assertQuery(
            ("POST", "/users/setFlags"),
            200,
            json={"user": user1["id"], "permission": True, "external": False},
            recent_callbacks=[("GET", "/update/user/1")]
        )

        # Create and get the first communism object
        communism1 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 1,
                "description": "description1",
                "creator": user1["id"]
            },
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/create/communism/1")]
        ).json()
        self.assertListEqual([communism1], self.assertQuery(("GET", "/communisms?id=1"), 200).json())

        # User referenced by participant 2 doesn't exist, then it's created
        user2 = self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user2"},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/2")]
        ).json()

        # Create and get the second communism object
        response2 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 42,
                "description": "description2",
                "creator": user1["id"]
            },
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/create/communism/2")]
        )
        communism2 = response2.json()
        self.assertListEqual([communism2], self.assertQuery(("GET", "/communisms?id=2"), 200).json())

        # Allow the user 2 to create communisms by vouching
        self.assertQuery(
            ("POST", "/users/setVoucher"),
            200,
            json={"debtor": user2["id"], "voucher": user1["id"]},
            recent_callbacks=[("GET", "/update/user/2")]
        )

        # Create and get the third communism object
        response3 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 1337,
                "description": "description3",
                "creator": user2["id"]
            },
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/create/communism/3")]
        )
        communism3 = response3.json()
        self.assertListEqual([communism3], self.assertQuery(("GET", "/communisms?id=3"), 200).json())

        # Add new users to the third communism
        for i in range(22):
            communism3_changed = self.assertQuery(
                ("POST", "/communisms/increaseParticipation"),
                200,
                json={"id": 3, "user": 1},
                r_schema=_schemas.Communism,
                recent_callbacks=[("GET", "/update/communism/3")]
            ).json()
            self.assertListEqual([communism3_changed], self.assertQuery(("GET", "/communisms?id=3"), 200).json())

        # Remove a user from the third communism
        communism3_changed = self.assertQuery(
            ("POST", "/communisms/decreaseParticipation"),
            200,
            json={"id": 3, "user": 1},
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/update/communism/3")]
        ).json()
        self.assertListEqual([communism3_changed], self.assertQuery(("GET", "/communisms?id=3"), 200).json())
        self.assertEqual(len(communism3_changed["participants"]), 2)
        self.assertEqual(communism3_changed["participants"][1]["quantity"], 21)

        # Modify the quantity of a user from the third communism
        communism3_changed = self.assertQuery(
            ("POST", "/communisms/increaseParticipation"),
            200,
            json={"id": 3, "user": 1},
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/update/communism/3")]
        ).json()
        query = "/communisms?active=true&unique_participants=2"
        self.assertListEqual([communism3_changed], self.assertQuery(("GET", query), 200).json())
        self.assertEqual(len(communism3_changed["participants"]), 2)
        self.assertEqual(communism3_changed["participants"][1]["quantity"], 22)

        # The newly added participant doesn't exist
        self.assertQuery(
            ("POST", "/communisms/setParticipants/3"),
            404,
            json=[_schemas.CommunismUserBinding(user_id=4, quantity=40)],
            recent_callbacks=[]
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

        # Add another new user to the communism
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user3"},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/create/user/3")]
        ).json()
        self.assertQuery(
            ("POST", "/users/setVoucher"),
            200,
            json={"debtor": 3, "voucher": 1},
            r_schema=_schemas.VoucherUpdateResponse,
            recent_callbacks=[("GET", "/update/user/3")]
        )
        self.assertQuery(
            ("POST", "/communisms/decreaseParticipation"),
            400,
            json={"id": 3, "user": 3}
        ).json()
        self.assertQuery(
            ("POST", "/communisms/increaseParticipation"),
            200,
            json={"id": 3, "user": 3},
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/update/communism/3")]
        ).json()

        # Do not allow another user to close the communism
        self.assertQuery(
            ("POST", "/communisms/close"),
            400,
            json={"id": 3, "issuer": 1}
        )
        self.assertQuery(
            ("POST", "/communisms/close"),
            404,
            json={"id": 3, "issuer": 10}
        )

        # Close the third communism and expect all balances to be adjusted (creator is participant!)
        users = self.assertQuery(("GET", "/users"), 200).json()
        self.assertEqual(self.assertQuery(("GET", "/transactions"), 200).json(), [])
        communism3_changed = self.assertQuery(
            ("POST", "/communisms/close"),
            200,
            json={"id": 3, "issuer": 2},
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

        # Check that the multi transaction worked as expected
        self.assertEqual(users[0]["balance"] - 1232, users_updated[0]["balance"])
        self.assertEqual(users[1]["balance"] + 1288, users_updated[1]["balance"])
        self.assertEqual(users[2]["balance"] - 56, users_updated[2]["balance"])

        # Updating a communism that doesn't exist or that is already closed shouldn't work
        self.assertListEqual([], self.assertQuery(("GET", "/communisms?id=4"), 200).json())
        self.assertQuery(
            ("POST", "/communisms/increaseParticipation"),
            404,
            json={"id": 4, "user": 3}
        ).json()
        self.assertQuery(
            ("POST", "/communisms/decreaseParticipation"),
            404,
            json={"id": 4, "user": 2}
        ).json()
        self.assertListEqual([communism3_changed], self.assertQuery(("GET", "/communisms?active=false"), 200).json())

        # Check that a multi transaction has been created by closing the communism
        time.sleep(0.1)
        session = self.get_db_session()
        self.assertEqual(1, len(session.query(models.MultiTransaction).all()))
        self.assertEqual(56, session.query(models.MultiTransaction).get(1).base_amount)

    def test_communism_schema_checks(self):
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

    def test_user_search(self):
        def comp(x: int, query: str):
            data = self.assertQuery(("GET", "/users" + (query and "?" + query)), 200).json()
            self.assertEqual(x, len(data), str(data))

        session = self.get_db_session()
        comp(0, "")

        session.add(models.User(active=False, external=False, permission=False))
        session.commit()
        comp(1, "")

        session.add(models.User(active=True, external=True, name="foo"))
        session.commit()
        comp(2, "")

        session.add(models.User(active=True, external=False, permission=True))
        session.add(models.User(active=True, external=False, permission=True, name="bar"))
        session.commit()
        comp(4, "")

        session.add(models.User(external=False, name="baz"))
        session.commit()
        comp(5, "")

        session.add(models.User(active=False, external=False, name="baz"))
        session.commit()
        comp(6, "")

        session.add(models.User(external=True, permission=False, voucher_id=3))
        session.commit()
        comp(7, "")

        comp(1, "id=1")
        comp(1, "id=2")
        comp(1, "id=3")

        comp(5, "active=true")
        comp(2, "active=false")

        comp(2, "external=true")
        comp(5, "external=false")

        comp(0, "name=foobar")
        comp(1, "name=foo")
        comp(2, "name=baz")

        comp(2, "active=true&external=false&permission=true")
        comp(1, "active=true&external=false&permission=true&name=bar")

        comp(1, "voucher_id=3")
        comp(0, "voucher_id=4")
        comp(0, "voucher_id=3&active=false")

        comp(2, "external=false&name=baz")
        comp(1, "external=false&name=baz&active=true")
        comp(1, "external=false&name=baz&active=false")

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
        comp(3, "alias_application_id=1")
        comp(0, "alias_application_id=2")
        comp(1, "alias_confirmed=false")
        comp(2, "alias_confirmed=true")
        comp(1, "alias_confirmed=true&alias_username=baz")
        comp(0, "alias_confirmed=true&alias_username=baz&id=1")

        session.close()


@_tested
class CallbackTests(utils.BaseAPITests):
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

        requests.get(f"{self.callback_server_uri}create/refund/7")
        requests.get(f"{self.callback_server_uri}update/user/3")
        requests.get(f"{self.callback_server_uri}delete/vote/1")
        self.assertEqual(("GET", "/create/refund/7"), self.callback_request_list.get(timeout=0.5))
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
