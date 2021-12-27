"""
MateBot unit tests for the whole API in certain user actions
"""

import time
import datetime
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
class WorkingAPITests(utils.BaseAPITests):
    def _set_user_attrs(self, uid: int, success: bool, **kwargs) -> dict:
        user = self.assertQuery(("GET", f"/users/{uid}"), 200).json()
        user.update(**kwargs)
        return self.assertQuery(
            ("PUT", "/users"),
            200 if success else [403, 404, 409],
            json=user,
            r_schema=_schemas.User if success else None,
            recent_callbacks=[("GET", "/refresh"), ("GET", f"/update/user/{uid}")] if success else None
        ).json()

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
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/callback/1")]
        )
        time.sleep(1)

        for u in users:
            self._set_user_attrs(u["id"], True)

        # Deleting valid models just works
        for i in range(3):
            self.assertQuery(
                ("DELETE", "/users"),
                204,
                json=users[-1],
                r_none=True,
                recent_callbacks=[("GET", "/refresh"), ("GET", f"/delete/user/{len(users)}")]
            )
            self.assertQuery(("GET", f"/users/{len(users)}"), 404, r_schema=_schemas.APIError)
            users.pop(-1)
            self.assertEqual(
                users,
                self.assertQuery(("GET", "/users"), 200, skip_callbacks=2).json()
            )

        # Deleting invalid models should fail
        user0 = users[0]
        user1 = users[1]
        user0["balance"] += 1
        self.assertQuery(("DELETE", "/users"), 409, json=user0, recent_callbacks=[])
        user0["balance"] -= 1
        user0_old_name = user0["name"]
        user0["name"] += "INVALID"
        self.assertQuery(("DELETE", "/users"), 409, json=user0, recent_callbacks=[])
        user0["name"] = user0_old_name
        user0 = self.assertQuery(("GET", f"/users/{user0['id']}"), 200).json()

        # Updating the balance, special flag, access times or aliases of a user should fail
        uid = user0["id"]
        self._set_user_attrs(uid, True, balance=0)
        self._set_user_attrs(uid, False, balance=1)
        # self._set_user_attrs(uid, False, special=True)
        self._set_user_attrs(uid, False, created=1337)
        self._set_user_attrs(uid, False, accessed=42)
        self._set_user_attrs(uid, False, aliases=[{
            "id": 1,
            "user_id": user0["id"],
            "application": "none",
            "app_user_id": "unknown@none",
            "confirmed": True
        }])
        self._set_user_attrs(uid, True)

        # Updating the name, permission/active/external flags and the voucher should work
        self._set_user_attrs(uid, True, external=True)
        self._set_user_attrs(uid, True, voucher=user1["id"])
        self._set_user_attrs(uid, True, permission=False)
        self._set_user_attrs(uid, True, active=False)
        self._set_user_attrs(uid, True, active=True)

        # Deleting users with balance != 0 should fail
        self.assertQuery(
            ("POST", "/transactions"),
            201,
            json={
                "sender": user0["id"],
                "receiver": user1["id"],
                "amount": 42,
                "reason": "test"
            },
            recent_callbacks=[("GET", "/refresh"), ("GET", f"/create/transaction/1")]
        )
        user0 = self.assertQuery(("GET", f"/users/{user0['id']}"), 200).json()
        user1 = self.assertQuery(("GET", f"/users/{user1['id']}"), 200).json()
        self.assertEqual(user0["balance"], -user1["balance"])
        self.assertQuery(("PUT", "/users"), 200, json=user0, r_schema=_schemas.User(**user0), skip_callbacks=2)
        self.assertQuery(("DELETE", "/users"), 409, json=user0)
        self.assertQuery(("DELETE", "/users"), 409, json=user1)

        # Deleting the user after fixing the balance should work again
        self.assertQuery(
            ("POST", "/transactions"),
            201,
            json={
                "sender": user1["id"],
                "receiver": user0["id"],
                "amount": 42,
                "reason": "reverse"
            },
            skip_callbacks=2,
            recent_callbacks=[("GET", "/refresh"), ("GET", f"/create/transaction/2")]
        )
        user0 = self.assertQuery(("GET", f"/users/{user0['id']}"), 200).json()
        user1 = self.assertQuery(("GET", f"/users/{user1['id']}"), 200).json()
        self.assertEqual(user0["balance"], 0)
        self.assertEqual(user1["balance"], 0)
        self.assertQuery(
            ("DELETE", "/users"),
            204,
            json=user0,
            r_none=True,
            recent_callbacks=[("GET", "/refresh"), ("GET", f"/delete/user/{user0['id']}")]
        )
        users.pop(0)

        # Deleting users that created an active communism shouldn't work
        user0 = users[0]
        user1 = users[1]
        communism = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json={
                "amount": 1337,
                "description": "description",
                "creator": user0["id"],
                "active": True,
                "externals": 0,
                "participants": [{"quantity": 1, "user": user1["id"]}]
            },
            recent_callbacks=[("GET", "/refresh"), ("GET", f"/create/communism/1")]
        ).json()
        self.assertQuery(("DELETE", "/users"), 409, json=user0, recent_callbacks=[])
        self.assertEqual(communism, self.assertQuery(("GET", "/communisms/1"), 200).json())

        # Deleting users that participate in active communisms shouldn't work
        self.assertQuery(("DELETE", "/users"), 409, json=user1, recent_callbacks=[])
        communism["participants"] = []
        self.assertQuery(("PUT", "/communisms"), 200, json=communism, r_schema=_schemas.Communism, skip_callbacks=2)
        self.assertQuery(
            ("DELETE", "/users"),
            204,
            json=user1,
            r_none=True,
            skip_callbacks=2,
            skip_callback_timeout=0.1,
            recent_callbacks=[("GET", "/refresh"), ("GET", f"/delete/user/{user1['id']}")]
        )
        users.pop(1)

        # Deleting the aforementioned user after closing the communism should work
        communism["active"] = False
        transactions = self.assertQuery(("GET", "/transactions"), 200).json()
        self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism,
            r_schema=_schemas.Communism
        )
        user0 = self.assertQuery(("GET", f"/users/{user0['id']}"), 200).json()
        self.assertEqual(0, user0["balance"])
        self.assertEqual(transactions, self.assertQuery(("GET", "/transactions"), 200).json())
        self.assertQuery(
            ("DELETE", "/users"),
            204,
            json=user0,
            r_none=True,
            skip_callbacks=4,
            skip_callback_timeout=0.1,
            recent_callbacks=[("GET", "/refresh"), ("GET", f"/delete/user/{user0['id']}")]
        )
        users.pop(0)

        self.assertEqual(users, self.assertQuery(("GET", "/users"), 200).json())
        self.assertEqual(len(users), 4, "Might I miss something?")

    def test_polls_and_votes(self):
        self.assertListEqual([], self.assertQuery(("GET", "/polls"), 200).json())

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/callback/1")]
        )

        # User referenced by 'user_id' doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/votes"),
            404,
            json={"user_id": 1, "poll_id": 1, "vote": 1}
        )
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user1", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/user/1")]
        ).json()

        # Poll referenced by 'poll_id' doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/votes"),
            404,
            json={"user_id": 1, "poll_id": 1, "vote": 1}
        )
        poll1 = self.assertQuery(
            ("POST", "/polls"),
            201,
            json={"question": "Is this a question?", "changeable": True},
            r_schema=_schemas.Poll,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/poll/1")]
        ).json()
        self.assertEqual(poll1["question"], "Is this a question?")

        # Add another poll to be sure
        poll2 = self.assertQuery(
            ("POST", "/polls"),
            201,
            json={"question": "Are you sure?", "changeable": False},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/poll/2")]
        ).json()
        self.assertEqual(poll2["votes"], [])
        self.assertEqual(poll2["changeable"], False)

        # Add the vote once, but not twice, even not with another vote
        vote1 = self.assertQuery(
            ("POST", "/votes"),
            201,
            json={"user_id": 1, "poll_id": 1, "vote": 1},
            r_schema=_schemas.Vote,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/vote/1")]
        )
        self.assertEqual(vote1.json()["vote"], 1)
        for v in [1, 0, -1]:
            self.assertQuery(
                ("POST", "/votes"),
                409,
                json={"user_id": 1, "poll_id": 1, "vote": v}
            )

        # Update the vote to become negative
        vote1_json = vote1.json()
        vote1_json["vote"] = -1
        vote1_json_updated = self.assertQuery(
            ("PUT", "/votes"),
            200,
            json=vote1_json,
            r_schema=_schemas.Vote,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/vote/1")]
        ).json()
        self.assertEqual(vote1_json_updated["vote"], -1)

        # Add another user for testing a second voting user
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user2", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/user/2")]
        )
        self.assertQuery(
            ("POST", "/votes"),
            201,
            json={"user_id": 2, "poll_id": 1, "vote": -1},
            r_schema=_schemas.Vote,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/vote/2")]
        )

        # Don't allow to change a vote of a restricted (unchangeable) poll
        vote3 = self.assertQuery(
            ("POST", "/votes"),
            201,
            json={"user_id": 2, "poll_id": 2, "vote": -1},
            r_schema=_schemas.Vote,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/vote/3")]
        )
        vote3_json = vote3.json()
        vote3_json["vote"] = 1
        self.assertQuery(
            ("PUT", "/votes"),
            409,
            json=vote3_json
        )
        self.assertQuery(
            ("PUT", "/votes"),
            409,
            json=vote3_json
        )

        # Try to close the poll with an old model
        poll1["active"] = False
        self.assertQuery(
            ("PUT", "/polls"),
            403,
            json=poll1
        )

        # Close the poll, then try closing it again
        poll1 = self.assertQuery(
            ("GET", "/polls/1"),
            200
        ).json()
        poll1["active"] = False
        poll1_updated = self.assertQuery(
            ("PUT", "/polls"),
            200,
            json=poll1,
            r_schema=_schemas.Poll,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/poll/1")]
        ).json()
        self.assertNotEqual(poll1, poll1_updated)
        self.assertEqual(poll1_updated["result"], -2)
        self.assertGreaterEqual(poll1_updated["closed"], int(datetime.datetime.now().timestamp()) - 1)
        self.assertEqual(poll1_updated["votes"], [
            self.assertQuery(("GET", "/votes/1"), 200).json(),
            self.assertQuery(("GET", "/votes/2"), 200).json(),
        ])
        self.assertQuery(
            ("PUT", "/polls"),
            200,
            json=poll1_updated,
            r_schema=_schemas.Poll(**poll1_updated),
            recent_callbacks=[]
        ).json()

        # Try adding new votes with another user to the closed poll
        self.assertQuery(
            ("POST", "/votes"),
            409,
            json={"user_id": 2, "poll_id": 1, "vote": -1}
        )

        # Open a new poll and close it immediately
        poll3 = self.assertQuery(
            ("POST", "/polls"),
            201,
            json={"question": "Why did you even open this poll?", "changeable": False},
            r_schema=_schemas.Poll
        )
        poll3_json = poll3.json()
        self.assertTrue(poll3_json["active"])
        poll3_json["active"] = False
        poll3_closed = self.assertQuery(
            ("PUT", "/polls"),
            200,
            json=poll3_json,
            r_schema=_schemas.Poll
        ).json()
        self.assertEqual(poll3_closed["result"], 0)
        self.assertEqual(poll3_closed["active"], False)
        self.assertEqual(poll3_closed["changeable"], False)
        self.assertEqual(poll3_closed["votes"], [])

    def test_refunds(self):
        self.assertListEqual([], self.assertQuery(("GET", "/refunds"), 200).json())

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/callback/1")]
        )

        # User referenced by 'creator' doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/refunds"),
            404,
            json={"description": "Foo", "amount": 1337, "creator": 1}
        ).json()
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user1", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/user/1")]
        ).json()

        # Poll referenced by 'poll_id' doesn't exist, then it's created by the refund
        self.assertQuery(
            ("POST", "/votes"),
            404,
            json={"user_id": 1, "poll_id": 1, "vote": 1}
        )
        refund1 = self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Foo", "amount": 1337, "creator": 1},
            r_schema=_schemas.Refund,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/refund/1")]
        ).json()
        self.assertTrue(refund1["active"])
        self.assertIsNone(refund1["allowed"])
        self.assertIsNone(refund1["transaction"])
        self.assertIsNotNone(refund1["created"])
        self.assertIsNotNone(refund1["accessed"])

        # The refund should not be closed now but can be deleted
        poll1 = self.assertQuery(("GET", "/polls/1"), 200).json()
        self.assertTrue(poll1["active"])
        self.assertQuery(("PUT", "/refunds"), 200, json=refund1)
        refund1["active"] = False
        self.assertQuery(("PUT", "/refunds"), 409, json=refund1)
        self.assertQuery(
            ("DELETE", "/refunds"),
            204,
            json=self.assertQuery(("GET", "/refunds/1"), 200).json(),
            r_is_json=False,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/delete/refund/1")]
        )
        poll1 = self.assertQuery(("GET", "/polls/1"), 200).json()
        self.assertFalse(poll1["active"])

        # A new refund creates a new poll as well
        refund2 = self.assertQuery(
            ("POST", "/refunds"),
            201,
            json={"description": "Bar", "amount": 1337, "creator": 1},
            r_schema=_schemas.Refund,
            recent_callbacks=[("GET", "/refresh")]
        ).json()
        self.assertEqual(self.assertQuery(("GET", "/polls/2"), 200, skip_callbacks=1).json()["votes"], [])
        self.assertEqual(2, len(self.assertQuery(("GET", "/polls"), 200).json()))

    def test_communisms(self):
        self.assertListEqual([], self.assertQuery(("GET", "/communisms"), 200).json())

        # Creating some working sample data for the unit test
        sample_data = [
            {
                "amount": 1,
                "description": "description1",
                "creator": 1,
                "active": True,
                "externals": 0,
                "participants": []
            },
            {
                "amount": 42,
                "description": "description2",
                "creator": 1,
                "active": True,
                "externals": 2,
                "participants": [
                    {
                        "user": 1,
                        "quantity": 1
                    },
                    {
                        "user": 2,
                        "quantity": 2
                    }
                ]
            },
            {
                "amount": 1337,
                "description": "description3",
                "creator": 2
            }
        ]

        # Adding the callback server for testing
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/callback/1")]
        )

        # User referenced by 'creator' doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/communisms"),
            404,
            json=sample_data[0]
        )
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user1", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/user/1")]
        )

        # Create and get the first communism object
        communism1 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json=sample_data[0],
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/communism/1")]
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
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user2", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/user/2")]
        )

        # Create and get the second communism object
        response2 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json=sample_data[1],
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/communism/2")]
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
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/communism/2")]
        ).json()

        # Create and get the third communism object
        response3 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json=sample_data[2],
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/communism/3")]
        )
        communism3 = response3.json()
        self.assertEqual(communism3["externals"], 0)
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
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/communism/2")]
        )

        # Add new users to the third communism
        communism3["participants"] = [
            _schemas.CommunismUserBinding(user=1, quantity=10).dict(),
            _schemas.CommunismUserBinding(user=2, quantity=20).dict()
        ]
        response3_changed = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/communism/3")]
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
            _schemas.CommunismUserBinding(user=1, quantity=10).dict()
        ]
        communism3_changed = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/communism/3")]
        ).json()
        self.assertEqual(communism3_changed, communism3)
        self.assertQuery(
            ("GET", "/communisms/3"),
            200,
            r_schema=communism3_changed
        )

        # Modify the quantity of a user from the third communism
        communism3["participants"] = [
            _schemas.CommunismUserBinding(user=1, quantity=40).dict()
        ]
        communism3 = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism(**communism3),
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/communism/3")]
        ).json()

        # Add and modify users from the third communism
        communism3["externals"] += 2
        communism3["participants"] = [
            _schemas.CommunismUserBinding(user=1, quantity=10).dict(),
            _schemas.CommunismUserBinding(user=2, quantity=3).dict(),
            _schemas.CommunismUserBinding(user=3, quantity=7).dict()
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
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/user/3")]
        )
        communism3 = self.assertQuery(
            ("PUT", "/communisms"),
            200,
            json=communism3,
            r_schema=_schemas.Communism(**communism3),
            r_schema_ignored_fields=["accessed", "created"],
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/communism/3")]
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
            {"user": 1, "quantity": 10},
            {"user": 1, "quantity": 10},
            {"user": 1, "quantity": 10},
            {"user": 2, "quantity": 20}
        ]
        self.assertQuery(
            ("PUT", "/communisms"),
            400,
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
                ("GET", "/refresh"), ("GET", "/update/communism/3"),
                ("GET", "/refresh"), ("GET", "/create/multitransaction/1")
            ]
        ).json()
        self.assertFalse(communism3_changed["active"])
        self.assertIsNotNone(communism3_changed["accessed"])
        self.assertIsNotNone(communism3_changed["created"])
        users_updated = self.assertQuery(("GET", "/users"), 200).json()
        transactions = self.assertQuery(("GET", "/transactions"), 200).json()
        multi_transactions = self.assertQuery(("GET", "/transactions/multi"), 200).json()
        self.assertEqual(2, len(transactions))
        self.assertEqual(1, len(multi_transactions))
        m = multi_transactions[0]
        del m["timestamp"], m["transactions"][0]["timestamp"], m["transactions"][1]["timestamp"]
        self.assertEqual(m, {
            "id": 1,
            "base_amount": 67,
            "total_amount": 1139,
            "transactions": [
                {
                    "id": 1,
                    "sender": 1,
                    "receiver": 2,
                    "amount": 670,
                    "reason": "communism[1]: description3",
                    "multi_transaction": 1
                },
                {
                    "id": 2,
                    "sender": 3,
                    "receiver": 2,
                    "amount": 469,
                    "reason": "communism[2]: description3",
                    "multi_transaction": 1
                }
            ]
        })
        self.assertEqual(users[0]["balance"], users_updated[0]["balance"] + 670)
        self.assertEqual(users[1]["balance"], users_updated[1]["balance"] - 1139)
        self.assertEqual(users[2]["balance"], users_updated[2]["balance"] + 469)

        # Updating a closed communism should yield HTTP 409
        self.assertQuery(
            ("PUT", "/communisms"),
            409,
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
        requests.get(f"{self.callback_server_uri}refresh")
        self.assertEqual(("GET", "/refresh"), self.callback_request_list.get(timeout=1))
        requests.get(f"{self.callback_server_uri}refresh")
        requests.get(f"{self.callback_server_uri}refresh")
        requests.get(f"{self.callback_server_uri}refresh")
        self.assertEqual(("GET", "/refresh"), self.callback_request_list.get(timeout=1))
        self.assertEqual(("GET", "/refresh"), self.callback_request_list.get(timeout=0))
        self.assertEqual(("GET", "/refresh"), self.callback_request_list.get(timeout=0))

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
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/refresh")]
        )
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": "http://localhost:64000"},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/callback/2")],
            skip_callbacks=1,
            skip_callback_timeout=0.2
        )
        self.assertQuery(
            ("POST", "/callbacks"),
            404,
            json={"base": "http://localhost:65000", "app": 1}
        )


if __name__ == '__main__':
    _unittest.main()
