"""
MateBot unit tests for the whole API in certain user actions
"""

import uuid
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
class UninitializedAPITests(utils.BaseAPITests):
    def _init_project_data(self):
        pass


@_tested
class WorkingAPITests(utils.BaseAPITests):
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
                self.assertQuery(("GET", "/users"), 200, skip_callbacks=2).json()
            )

    def test_ballots_and_votes(self):
        self.assertListEqual([], self.assertQuery(("GET", "/ballots"), 200).json())

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
            json={"user_id": 1, "ballot_id": 1, "vote": 1}
        )
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user1", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/user/1")]
        ).json()

        # Ballot referenced by 'ballot_id' doesn't exist, then it's created
        self.assertQuery(
            ("POST", "/votes"),
            404,
            json={"user_id": 1, "ballot_id": 1, "vote": 1}
        )
        self.assertEqual(
            self.assertQuery(
                ("POST", "/ballots"),
                201,
                json={"question": "Is this a question?", "restricted": False},
                r_schema=_schemas.Ballot,
                recent_callbacks=[("GET", "/refresh"), ("GET", "/create/ballot/1")]
            ).json()["question"],
            "Is this a question?"
        )

        # Add another ballot to be sure
        ballot2 = self.assertQuery(
            ("POST", "/ballots"),
            201,
            json={"question": "Are you sure?", "restricted": True},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/ballot/2")]
        ).json()
        self.assertEqual(ballot2["votes"], [])
        self.assertEqual(ballot2["restricted"], True)

        # Add the vote once, but not twice, even not with another vote
        vote1 = self.assertQuery(
            ("POST", "/votes"),
            201,
            json={"user_id": 1, "ballot_id": 1, "vote": 1},
            r_schema=_schemas.Vote,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/vote/1")]
        )
        self.assertEqual(vote1.json()["vote"], 1)
        for v in [1, 0, -1]:
            self.assertQuery(
                ("POST", "/votes"),
                409,
                json={"user_id": 1, "ballot_id": 1, "vote": v}
            )

        # Update the vote to become negative
        vote1 = self.assertQuery(
            ("PATCH", "/votes"),
            200,
            json={"id": 1, "vote": -1},
            headers={"If-Match": vote1.headers.get("ETag")},
            r_schema=_schemas.Vote,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/vote/1")]
        ).json()
        self.assertEqual(vote1["vote"], -1)

        # Add another user for testing a second voting user
        self.assertQuery(
            ("POST", "/users"),
            201,
            json={"name": "user2", "permission": True, "external": False},
            r_schema=_schemas.User,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/user/2")]
        )
        vote2 = self.assertQuery(
            ("POST", "/votes"),
            201,
            json={"user_id": 2, "ballot_id": 1, "vote": -1},
            r_schema=_schemas.Vote,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/vote/2")]
        ).json()

        # Don't allow to change a vote of a restricted ballot
        vote3 = self.assertQuery(
            ("POST", "/votes"),
            201,
            json={"user_id": 2, "ballot_id": 2, "vote": -1},
            r_schema=_schemas.Vote,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/vote/3")]
        )
        self.assertQuery(
            ("PATCH", "/votes"),
            412,
            json={"id": 3, "vote": 1}
        )
        self.assertQuery(
            ("PATCH", "/votes"),
            409,
            json={"id": 3, "vote": 1},
            headers={"If-Match": vote3.headers.get("ETag")}
        )

        # Close the ballot, then try closing it again
        ballot1_etag = self.assertQuery(
            ("GET", "/ballots/1"),
            200,
            r_schema=_schemas.Ballot
        ).headers.get("ETag")
        ballot1_closed_response = self.assertQuery(
            ("PATCH", "/ballots"),
            200,
            json={"id": 1},
            r_schema=_schemas.Ballot,
            headers={"If-Match": ballot1_etag},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/ballot/1")]
        )
        ballot1 = ballot1_closed_response.json()
        self.assertQuery(
            ("PATCH", "/ballots"),
            200,
            json={"id": 1},
            headers={"If-Match": ballot1_closed_response.headers.get("ETag")},
            r_schema=_schemas.Ballot(**ballot1)
        )
        self.assertEqual(ballot1["result"], -2)
        self.assertGreaterEqual(ballot1["closed"], int(datetime.datetime.now().timestamp()) - 1)
        self.assertEqual(ballot1["votes"], [vote1, vote2])

        # Try adding new votes with another user to the closed ballot
        self.assertQuery(
            ("POST", "/votes"),
            409,
            json={"user_id": 2, "ballot_id": 1, "vote": -1}
        )

        # Open a new ballot and close it immediately
        self.assertTrue(
            self.assertQuery(
                ("POST", "/ballots"),
                201,
                json={"question": "Why did you even open this ballot?", "restricted": True},
                r_schema=_schemas.Ballot
            ).json()["active"]
        )
        ballot3_closed = self.assertQuery(
            ("PATCH", "/ballots"),
            200,
            json={"id": 3},
            r_schema=_schemas.Ballot
        ).json()
        self.assertEqual(ballot3_closed["result"], 0)
        self.assertEqual(ballot3_closed["active"], False)
        self.assertEqual(ballot3_closed["restricted"], True)
        self.assertEqual(ballot3_closed["votes"], [])

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
                "amount": 100,
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

        # Create and get the third communism object
        response3 = self.assertQuery(
            ("POST", "/communisms"),
            201,
            json=sample_data[2],
            r_schema=_schemas.Communism,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/communism/3")]
        )
        communism3 = response3.json()
        self.assertQuery(
            ("GET", "/communisms/3"),
            200,
            r_schema=_schemas.Communism(**communism3)
        ).json()

        # Omit the If-Match header entirely even though enforced
        self.assertQuery(
            ("PATCH", "/communisms"),
            412,
            json={"id": 2}
        )

        # Try updating with a wrong If-Match header (which should fail)
        self.assertQuery(
            ("PATCH", "/communisms"),
            412,
            json={"id": 2},
            headers={"If-Match": "Definitively-Wrong"}
        )
        self.assertQuery(
            ("PATCH", "/communisms"),
            412,
            json={"id": 2},
            headers={"If-Match": str(uuid.uuid4())}
        )

        # Do an empty patch operation (that shouldn't change anything)
        self.assertQuery(
            ("PATCH", "/communisms"),
            200,
            json={"id": 2},
            headers={"If-Match": response2.headers.get("ETag")},
            r_schema=communism2,
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/communism/2")]
        )

        # Add new users to the third communism
        response3_patched = self.assertQuery(
            ("PATCH", "/communisms"),
            200,
            json={
                "id": 3,
                "participants": [
                    {"user": 1, "quantity": 10},
                    {"user": 2, "quantity": 20}
                ]
            },
            r_schema=_schemas.Communism,
            headers={"If-Match": response3.headers.get("ETag")},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/update/communism/3")]
        )
        communism3_patched = response3_patched.json()
        communism3["participants"] = [
            _schemas.CommunismUserBinding(user=1, quantity=10).dict(),
            _schemas.CommunismUserBinding(user=2, quantity=20).dict()
        ]
        self.assertEqual(communism3_patched, communism3)
        self.assertQuery(
            ("GET", "/communisms/3"),
            200,
            r_schema=communism3_patched
        )

        # Do not allow to delete the first communism
        self.assertQuery(
            ("DELETE", "/communisms"),
            [400, 405]
        )

        # Forbid to update a communism if a user is mentioned twice or more
        self.assertQuery(
            ("PATCH", "/communisms"),
            400,
            json={
                "id": 3,
                "participants": [
                    {"user": 1, "quantity": 10},
                    {"user": 1, "quantity": 10},
                    {"user": 1, "quantity": 10},
                    {"user": 2, "quantity": 20}
                ]
            },
            headers={"If-Match": response3_patched.headers.get("ETag")}
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

        requests.get(f"{self.callback_server_uri}create/ballot/7")
        requests.get(f"{self.callback_server_uri}update/user/3")
        requests.get(f"{self.callback_server_uri}delete/vote/1")
        self.assertEqual(("GET", "/create/ballot/7"), self.callback_request_list.get(timeout=0.5))
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
