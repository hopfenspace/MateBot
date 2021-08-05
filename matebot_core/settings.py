"""
MateBot core settings provider
"""

import os
import sys
from typing import Any, Dict, Tuple

try:
    import ujson as json
except ImportError:
    import json

import pydantic
from pydantic.env_settings import SettingsSourceCallable as _SettingsSourceCallable

from .schemas import config


CONFIG_PATHS = ["config.json", os.path.join("..", "config.json")]


def _read_config_from_json_source(_: pydantic.BaseSettings) -> Dict[str, Any]:
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            with open(path, "r", encoding="UTF-8") as file:
                return json.load(file)
    else:
        print(
            "No config file found! Add a 'config.json' file to your project. "
            "The server will start with default settings in the meantime.",
            file=sys.stderr
        )
        return _get_default_config()


class Settings(pydantic.BaseSettings, config.CoreConfig):
    """
    MateBot core settings
    """

    class Config:
        @classmethod
        def customise_sources(
                cls,
                init_settings: _SettingsSourceCallable,
                env_settings: _SettingsSourceCallable,
                file_secret_settings: _SettingsSourceCallable
        ) -> Tuple[_SettingsSourceCallable, ...]:
            return _read_config_from_json_source, init_settings, env_settings, file_secret_settings


def _get_default_config() -> Dict[str, Any]:
    return config.CoreConfig(
        general=config.GeneralConfig(),
        community=config.CommunityConfig(),
        logging=config.LoggingConfig(),
        database=config.DatabaseConfig()
    ).dict()
