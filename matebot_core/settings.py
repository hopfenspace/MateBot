"""
MateBot core settings provider
"""

import os
import sys
from typing import Any, Dict, Optional, Tuple

try:
    import ujson as json
except ImportError:
    import json

import pydantic
from pydantic.env_settings import SettingsSourceCallable as _SettingsSourceCallable

from .schemas import config


CONFIG_PATHS = ["config.json", os.path.join("..", "config.json")]
if os.environ.get("CONFIG_PATH"):
    CONFIG_PATHS = [os.environ.get("CONFIG_PATH")]


def read_settings_from_json_source(create: bool = False) -> Optional[Dict[str, Any]]:
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            with open(path, "r", encoding="UTF-8") as file:
                return json.load(file)
    if not create:
        return
    with open(CONFIG_PATHS[0], "w") as f:
        json.dump(get_default_config(), f, indent=4)
    return read_settings_from_json_source(False)


class Settings(pydantic.BaseSettings, config.CoreConfig):
    """
    MateBot core settings

    Do not change most of the settings at runtime, since this might lead to unspecified
    behavior. Always restart the server after changing the config file. But note that
    there are some parts (especially the server config and the database config), which
    might get overwritten during initialization (via command-line arguments) or during
    unit testing (where e.g. some server settings will be ignored completely).
    """

    class Config:
        env_nested_delimiter = "__"
        env_file = ".env"

        @classmethod
        def customise_sources(
                cls,
                init_settings: _SettingsSourceCallable,
                env_settings: _SettingsSourceCallable,
                file_secret_settings: _SettingsSourceCallable
        ) -> Tuple[_SettingsSourceCallable, ...]:
            return env_settings, file_secret_settings, read_settings_from_config_file, init_settings


def read_settings_from_config_file(_: Optional[pydantic.BaseSettings]) -> Dict[str, Any]:
    settings = read_settings_from_json_source(create=False)
    if not settings:
        print(
            f"No config file found! Use the 'init' command to create a basic configuration file. "
            f"Afterwards, apply the database migrations and use 'init' once again.",
            file=sys.stderr
        )
        sys.exit(1)
    return settings


def get_default_config() -> Dict[str, Any]:
    return config.CoreConfig(
        general=config.GeneralConfig(),
        server=config.ServerConfig(),
        logging=config.LoggingConfig(),
        database=config.DatabaseConfig()
    ).dict()
