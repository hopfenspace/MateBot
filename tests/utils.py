"""
Helper functions to make writing unit tests for the MateBot core easier
"""

import os
import sys
import random
import string
import unittest
import subprocess
from typing import Optional

from . import conf


class BaseTest(unittest.TestCase):
    """
    A base class for unit tests which introduces simple setup and teardown of unit tests

    If a subclass needs special setup or teardown functionality, it **MUST**
    call the superclasses setup and teardown methods: the superclass setup
    method at the beginning of the subclass setup method, the superclass
    teardown method at the end of the subclass teardown method.
    """

    database_url: str
    _database_file: Optional[str] = None

    def setUp(self) -> None:
        if conf.DATABASE_URL is not None:
            self.database_url = conf.DATABASE_URL
            for k in ["COMMAND_INITIALIZE_DATABASE", "COMMAND_CLEANUP_DATABASE"]:
                if not hasattr(conf, k):
                    print(
                        f"Mandatory config variable {k!r} not found in config file!",
                        file=sys.stderr
                    )
                    sys.exit(1)
                if getattr(conf, k) is None:
                    print(
                        f"{k!r} has not been set (value: None)! This config value "
                        "is mandatory for non-default databases. Any unittest may fail. "
                        "But if you really need no script(s), set it to an empty list.",
                        file=sys.stderr
                    )
                    sys.exit(1)

            if conf.COMMAND_INITIALIZE_DATABASE:
                subprocess.run(conf.COMMAND_INITIALIZE_DATABASE)

        else:
            self._database_file = conf.DATABASE_DEFAULT_FILE_FORMAT.format(
                os.getpid(),
                "".join([random.choice(string.ascii_lowercase) for _ in range(6)])
            )

            try:
                open(self._database_file, "wb").close()
                os.remove(self._database_file)
                self.database_url = conf.DATABASE_URL_FORMAT.format(self._database_file)

            except OSError as exc:
                self.database_url = conf.DATABASE_FALLBACK_URL
                self._database_file = None
                print(
                    f"{exc}: Falling back to in-memory database. This is not recommended!",
                    file=sys.stderr
                )

    def tearDown(self) -> None:
        if conf.DATABASE_URL is not None and conf.COMMAND_CLEANUP_DATABASE:
            subprocess.run(conf.COMMAND_CLEANUP_DATABASE)

        elif self.database_url != conf.DATABASE_FALLBACK_URL and self._database_file:
            if os.path.exists(self._database_file):
                os.remove(self._database_file)
