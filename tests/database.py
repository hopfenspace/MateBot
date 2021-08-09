"""
Helper functions to interact with databases during MateBot unit testing
"""

import os
import sys
import random
import string
from typing import Callable, Optional


# The placeholders will be filled by the PID and a random nonce or the database file location
_DATABASE_DEFAULT_FILE_FORMAT: str = "/tmp/unittest_{}_{}.db"
_DATABASE_URL_FORMAT: str = "sqlite:///{}"
_DATABASE_FALLBACK_URL: str = "sqlite://"

# If you want to manually overwrite the database location (and therefore
# allow other databases than sqlite), then you want to set this variable
OVERWRITE_DB_URL: Optional[str] = None


def get_database_url(
        file_location: Optional[str] = None,
        log_errors: bool = True
) -> (str, Callable[[], None]):
    """
    Create a database URL using a sqlite3 database which was confirmed to be accessible

    This function receives a file location which will be the preferred location
    of the sqlite3 database. It will be checked that the current user has the
    permissions to create, write and remove that file. If the ``OVERWRITE_DB_URL``
    global variable has been set, it will be preferred over any sqlite3
    database file to allow customization and testing other database providers.
    Since just about any URL could be given in that variable, there is no
    possibility to perform clean-up actions after every unit test in this case.
    Note that this function returns a in-memory sqlite3 database on failure.

    :param file_location: optional preferred location of the database file
    :param log_errors: switch to enable error logging to sys.stderr
    :return: tuple of the database string and a cleanup function which
        should be called after all database operations were finished
    """

    if OVERWRITE_DB_URL is not None:
        return OVERWRITE_DB_URL, lambda: None

    if file_location is None:
        file_location = _DATABASE_DEFAULT_FILE_FORMAT.format(
            os.getpid(),
            "".join([random.choice(string.ascii_lowercase) for _ in range(6)])
        )

    try:
        open(file_location, "wb").close()
        os.remove(file_location)
        db_url = _DATABASE_URL_FORMAT.format(file_location)
        return db_url, lambda: os.remove(file_location)

    except OSError as exc:
        if log_errors:
            print(
                exc,
                "Falling back to in-memory database. This is not recommended!",
                sep="\n",
                file=sys.stderr
            )

    return _DATABASE_FALLBACK_URL, lambda: None
