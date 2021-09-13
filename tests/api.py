"""
MateBot unit tests for the whole API in certain user actions
"""

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
                r_schema=_schemas.User,
                total_callbacks=0
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
        self.assertListEqual([], self.callback_request_list)
        requests.get(f"{self.callback_server_uri}refresh")
        self.assertListEqual([("GET", "/refresh")], self.callback_request_list)
        requests.get(f"{self.callback_server_uri}refresh")
        requests.get(f"{self.callback_server_uri}refresh")
        requests.get(f"{self.callback_server_uri}refresh")
        self.assertTrue(all(map(lambda x: x == ("GET", "/refresh"), self.callback_request_list)))

        requests.get(f"{self.callback_server_uri}create/ballot/7")
        requests.get(f"{self.callback_server_uri}update/user/3")
        requests.get(f"{self.callback_server_uri}delete/vote/1")
        self.assertListEqual(
            [("GET", "/create/ballot/7"), ("GET", "/update/user/3"), ("GET", "/delete/vote/1")],
            self.callback_request_list[-3:]
        )
        self.assertTrue(all(map(lambda x: x[0] == "GET", self.callback_request_list)))

    def test_callback_helper(self):
        self.assertListEqual([], self.callback_request_list)
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": f"http://localhost:{self.callback_server_port}/"},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/callback/1")],
            total_callbacks=2
        )
        self.assertQuery(
            ("POST", "/callbacks"),
            201,
            json={"base": "http://localhost:64000"},
            recent_callbacks=[("GET", "/refresh"), ("GET", "/create/callback/2")],
            total_callbacks=4
        )
        self.assertQuery(
            ("POST", "/callbacks"),
            404,
            json={"base": "http://localhost:65000", "app": 1},
            total_callbacks=4
        )


if __name__ == '__main__':
    _unittest.main()
