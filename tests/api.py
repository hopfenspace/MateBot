"""
MateBot unit tests for the whole API in certain user actions
"""

import os
import sys
import unittest
from typing import Optional


# The placeholders will be filled by the port and PID or the database file location
_DATABASE_FILE_FORMAT: str = "/tmp/api_unittest_{}_{}.db"
_DATABASE_URL_FORMAT: str = "sqlite:///{}"
_DATABASE_FALLBACK_URL: str = "sqlite://"

# If you want to manually overwrite the database location (and therefore
# allow other databases than sqlite, then you want to set this variable)
_DATABASE_OVERWRITE_URL: Optional[str] = None


def _get_database_url(port: int, pid: int) -> str:
    """
    Create a database URL using a sqlite3 database which was confirmed to be accessible
    """

    if _DATABASE_OVERWRITE_URL is not None:
        return _DATABASE_OVERWRITE_URL

    db_location = _DATABASE_FILE_FORMAT.format(port, pid)
    try:
        open(db_location, "wb").close()
        os.remove(db_location)
        db_url = _DATABASE_URL_FORMAT.format(db_location)

    except OSError as exc:
        db_url = _DATABASE_FALLBACK_URL
        print(
            exc,
            "Falling back to in-memory database. This is not recommended!",
            sep="\n",
            file=sys.stderr
        )

    return db_url


class _BaseAPITests(unittest.TestCase):
    server_port: int
    server_thread: threading.Thread


class WorkingAPITests(_BaseAPITests):
    pass


class FailingAPITests(_BaseAPITests):
    pass


def get_suite() -> unittest.TestSuite:
    suite = unittest.TestSuite()
    for cls in [WorkingAPITests, FailingAPITests]:
        for fixture in filter(lambda f: f.startswith("test_"), dir(cls)):
            suite.addTest(cls(fixture))
    return suite


if __name__ == '__main__':
    unittest.main()
