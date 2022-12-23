"""
MateBot unit tests for the CLI
"""

import os
import sys
import subprocess
import unittest as _unittest

import requests

from . import utils


class StandaloneCLITests(utils.BaseTest):
    SUBPROCESS_CATCH_STDERR = True
    SUBPROCESS_CATCH_STDOUT = True

    def test_help(self):
        self._run_cmd(0, "-h", no_defaults=True)
        self._run_cmd(0, "--help", no_defaults=True)
        self._run_cmd(0, "apps", "--help", no_defaults=True)
        self._run_cmd(0, "users", "--help", no_defaults=True)
        self._run_cmd(0, "init", "--help", no_defaults=True)
        self._run_cmd(0, "auto", "--help", no_defaults=True)
        self._run_cmd(0, "run", "--help", no_defaults=True)
        self._run_cmd(0, "systemd", "--help", no_defaults=True)

    def test_auto_mode(self):
        self._run_cmd(0, "auto", timeout=7.5, expect_timeout=True, terminate_process=False, SERVER__PORT="58888")
        self.assertTrue(requests.get("http://localhost:58888/v1").ok)

    def test_auto_mode_missing_db(self):
        self._run_cmd(1, "auto", no_defaults=True, CONFIG_PATH=self.config_file)
        self._run_cmd(1, "auto", no_defaults=True, CONFIG_PATH=self.config_file, SERVER__PORT="8888")

    def test_auto_mode_invalid_port(self):
        self._run_cmd(1, "auto", SERVER__PORT="66666")

    def test_run_apps_utilities(self):
        self._run_cmd(0, "init", "--database", self.database_url, no_defaults=True)
        self._run_cmd(0, "apps", "show", no_defaults=True)
        self._run_cmd(0, "apps", "add", "--app", "foo", "--password", "foo", timeout=10, no_defaults=True)
        self._run_cmd(0, "apps", "add", "--app", "bar", "--password", "bar", timeout=10, no_defaults=True)
        self._run_cmd(0, "apps", "show", no_defaults=True)
        self._run_cmd(0, "apps", "del", "bar", no_defaults=True)
        self._run_cmd(0, "apps", "show", no_defaults=True)
        self._run_cmd(1, "apps", "del", "bar", no_defaults=True)
        self._run_cmd(0, "apps", "show", no_defaults=True)

    def test_run_users_utilities(self):
        self._run_cmd(0, "init", "--database", self.database_url, no_defaults=True)
        self._run_cmd(0, "users", "-h", no_defaults=True)
        self._run_cmd(0, "users", "show", no_defaults=True)
        self._run_cmd(0, "users", "show", "--help", no_defaults=True)
        self._run_cmd(0, "users", "show", "--json", no_defaults=True)

    def test_init_command1(self):
        self._run_cmd(0, "init")

    def test_init_command2(self):
        self._run_cmd(0, "init", "--no-community", "--no-migrations")
        p1 = subprocess.Popen(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env={"CONFIG_PATH": self.config_file, "DATABASE__CONNECTION": self.database_url},
            stderr=subprocess.PIPE,
            stdout=subprocess.PIPE
        )
        type(self).SUBPROCESS_POOL.append(p1)
        p1.wait(2)
        self.assertEqual(0, p1.poll())
        self._run_cmd(0, "init", "--no-community", "--no-migrations")
        self._run_cmd(0, "init", "--no-community", "--no-migrations")
        self._run_cmd(0, "init", "--no-migrations")

    def test_init_command3(self):
        self._run_cmd(0, "init", "--database", self.database_url, "--community-name", "VeryCoolUser", no_defaults=True)

    def test_systemd(self):
        self._run_cmd(0, "systemd", "-h", no_defaults=True)
        target = os.path.join("/tmp", "test.service")
        self._run_cmd(0, "systemd", "--path", target, no_defaults=True)
        self.assertTrue(os.path.exists(target))
        self._run_cmd(1, "systemd", "--path", target, no_defaults=True)
        self._run_cmd(0, "systemd", "--force", "--path", target, no_defaults=True)
        os.unlink(target)


if __name__ == '__main__':
    _unittest.main()
