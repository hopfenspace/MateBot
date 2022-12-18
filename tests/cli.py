"""
MateBot unit tests for the CLI
"""

import sys
import subprocess
import unittest as _unittest

from . import utils


class StandaloneCLITests(utils.BaseTest):
    def test_help(self):
        p = subprocess.Popen([sys.executable, "-m", "matebot_core", "--help"])
        type(self).SUBPROCESS_POOL.append(p)
        p.wait(1)
        self.assertEqual(0, p.poll())

    def test_auto_mode(self):
        p = subprocess.Popen(
            [sys.executable, "-m", "matebot_core", "auto"],
            env={"CONFIG_PATH": self.config_file, "DATABASE__CONNECTION": self.database_url, "SERVER__PORT": "8888"}
        )
        type(self).SUBPROCESS_POOL.append(p)
        with self.assertRaises(subprocess.TimeoutExpired):
            p.wait(1.5)
        p.terminate()

    def test_auto_mode_missing_db(self):
        p = subprocess.Popen(
            [sys.executable, "-m", "matebot_core", "auto"],
            env={"CONFIG_PATH": self.config_file, "SERVER__PORT": "8888"}
        )
        type(self).SUBPROCESS_POOL.append(p)
        p.wait(1)
        self.assertEqual(1, p.poll())

    def test_auto_mode_invalid_port(self):
        p = subprocess.Popen(
            [sys.executable, "-m", "matebot_core", "auto"],
            env={"CONFIG_PATH": self.config_file, "DATABASE__CONNECTION": self.database_url, "SERVER__PORT": "66666"}
        )
        type(self).SUBPROCESS_POOL.append(p)
        p.wait(1)
        self.assertEqual(1, p.poll())

    def test_auto_help(self):
        p = subprocess.Popen([sys.executable, "-m", "matebot_core", "auto", "--help"])
        type(self).SUBPROCESS_POOL.append(p)
        p.wait(1)
        self.assertEqual(0, p.poll())

    def _run_init_cmd(self, return_code: int, *args, timeout: float = 2.5, no_defaults: bool = False, **kwargs):
        d = {} if no_defaults else {"CONFIG_PATH": self.config_file, "DATABASE__CONNECTION": self.database_url}
        d.update(kwargs)
        p = subprocess.Popen([sys.executable, "-m", "matebot_core", "init", *args], env=d)
        type(self).SUBPROCESS_POOL.append(p)
        p.wait(timeout)
        self.assertEqual(return_code, p.poll())

    def test_init_command1(self):
        self._run_init_cmd(0)

    def test_init_command2(self):
        self._run_init_cmd(0, "--no-community", "--no-migrations")
        p1 = subprocess.Popen(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            env={"CONFIG_PATH": self.config_file, "DATABASE__CONNECTION": self.database_url}
        )
        type(self).SUBPROCESS_POOL.append(p1)
        p1.wait(2)
        self.assertEqual(0, p1.poll())
        self._run_init_cmd(0, "--no-community", "--no-migrations")
        self._run_init_cmd(0, "--no-community", "--no-migrations")
        self._run_init_cmd(0, "--no-migrations")

    def test_init_command3(self):
        self._run_init_cmd(0, "--database", self.database_url, "--community-name", "VeryCoolUser", no_defaults=True)


if __name__ == '__main__':
    _unittest.main()
