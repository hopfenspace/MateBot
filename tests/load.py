"""
MateBot load testing of the API endpoints
"""

import time
import asyncio
import threading
import unittest as _unittest
from typing import Type

import aiohttp

from matebot_core import schemas as _schemas

from . import conf, utils


load_suite = _unittest.TestSuite()


def _tested(cls: Type):
    global load_suite
    for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
        load_suite.addTest(cls(fixture))
    return cls


@_tested
class LoadTests(utils.BaseAPITests):
    SUBPROCESS_CATCH_STDERR = False
    SUBPROCESS_CATCH_STDOUT = False

    def _run_load_tests(self, setup) -> float:
        self.login()

        async def query(count, endpoint, code, **kwargs):
            headers = {"Authorization": f"Bearer {self.token}"}
            async with aiohttp.ClientSession() as session:
                responses = await asyncio.gather(*[
                    session.request(endpoint[0], self.server + endpoint[1], headers=headers, **kwargs)
                    for _ in range(count)
                ])
            for r in responses:
                self.assertEqual(r.status, code)

        def run(*args, **kwargs):
            loop = asyncio.new_event_loop()
            loop.run_until_complete(query(*args, **kwargs))
            loop.run_until_complete(asyncio.sleep(0))
            loop.close()

        threads = [threading.Thread(daemon=True, target=run, args=entry[0], kwargs=entry[1]) for entry in setup]
        start = time.time()
        for t in threads:
            t.start()
        for t in threads:
            t.join()
        end = time.time()
        return end - start

    def test_invalid_requests(self):
        runtime = self._run_load_tests([
            ((1000, ("GET", "v1/unicorns"), 404), {}),
            ((1000, ("GET", "docs/v1"), 404), {}),
            ((1000, ("TRACE", "v1/users"), 405), {}),
            ((1000, ("POST", "v1/"), 405), {}),
            ((1000, ("IGNORE", ""), 400), {})  # yes, this is an invalid HTTP method
        ])
        self.assertLess(runtime, conf.LOAD_TEST_INVALID_REQUESTS, "too slow responses to invalid requests")

    def test_get_users(self):
        runtime = self._run_load_tests([
            ((500, ("GET", "v1/users"), 200), {}),
            ((100, ("GET", "v1/users?active=True"), 200), {}),
            ((100, ("GET", "v1/users?balance=0"), 200), {}),
            ((100, ("GET", "v1/users?id=1"), 200), {}),
            ((100, ("GET", "v1/users?special=False"), 200), {}),
            ((100, ("GET", "v1/users?special=True"), 200), {})
        ])
        self.assertLess(runtime, conf.LOAD_TEST_GET_USERS, "too slow GET users endpoints")

    def test_make_transactions(self):
        self.login()
        user1 = self.assertQuery(("POST", "/users"), 201, json={"name": "user1"}, r_schema=_schemas.User).json()
        user2 = self.assertQuery(("POST", "/users"), 201, json={"name": "user2"}, r_schema=_schemas.User).json()
        self._edit_user(user1["id"], permission=True, external=False, balance=8600000)
        self._edit_user(user2["id"], permission=True, external=False)
        data = {
            "sender": user1["id"],
            "receiver": user2["id"],
            "amount": 100,
            "reason": f"test"
        }
        runtime = self._run_load_tests([
            ((1000, ("POST", "v1/transactions/send"), 201), {"json": data})
        ])
        self.assertLess(runtime, conf.LOAD_TEST_MAKE_TRANSACTIONS, "too slow POST transactions endpoint")

    # See https://github.com/hopfenspace/MateBot/issues/118 for the origin of this test case
    def test_172_transactions(self):
        self.login()
        user1 = self.assertQuery(("POST", "/users"), 201, json={"name": "user1"}, r_schema=_schemas.User).json()
        user2 = self.assertQuery(("POST", "/users"), 201, json={"name": "user2"}, r_schema=_schemas.User).json()
        self._edit_user(user1["id"], permission=True, external=False, balance=8600000)
        self._edit_user(user2["id"], permission=True, external=False)

        for i in range(172):
            self.assertQuery(("POST", "/transactions/send"), 201, json={
                "sender": user1["id"],
                "receiver": user2["id"],
                "amount": 50000,
                "reason": f"test {i}"
            })
