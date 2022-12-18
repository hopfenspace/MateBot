"""
MateBot core settings provider
"""

import os
import sys
import functools
from typing import Any, Callable, Dict, List, Optional, Tuple

try:
    import ujson as json
except ImportError:
    import json

import pydantic
from pydantic.env_settings import SettingsSourceCallable as _SettingsSourceCallable

from .schemas import config


SETTINGS_CREATE_NONEXISTENT: bool = True
"""
switch to create a new configuration file if no existing file has been found
"""

SETTINGS_EXIT_ON_ERROR: bool = True
"""
switch to call ``exit(1)`` for failed config loading (use all defaults otherwise)
"""

SETTINGS_LOG_ERROR_FUNCTION: Optional[Callable[[str], Any]] = functools.partial(print, file=sys.stderr)
"""
optional function to accept log messages on failure
"""

SETTINGS_LOG_INFO_FUNCTION: Optional[Callable[[str], Any]] = None
"""
optional function to accept log messages when creating a new configuration file
"""

CONFIG_PATHS: List[str] = ["config.json", os.path.join("..", "config.json")]
"""
list of search paths for the config file, can be overwritten by the env variable ``CONFIG_PATH``
"""

if os.environ.get("CONFIG_PATH"):
    CONFIG_PATHS = [os.environ.get("CONFIG_PATH")]


def get_db_from_env(db_override: Optional[str] = None) -> Optional[str]:
    if db_override:
        return db_override
    return os.environ.get("DATABASE_CONNECTION", os.environ.get("DATABASE__CONNECTION", None))


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
            return env_settings, file_secret_settings, read_settings_from_file, init_settings, get_default_config


def store_configuration(conf: Optional[config.CoreConfig] = None, path: Optional[str] = None) -> config.CoreConfig:
    p = path or os.path.abspath(CONFIG_PATHS[0])
    conf = conf or get_default_core_config(get_db_from_env())
    with open(p, "w") as f:
        json.dump(conf.dict(), f, indent=4)
    SETTINGS_LOG_INFO_FUNCTION and SETTINGS_LOG_INFO_FUNCTION(f"A new config file has been created as {p!r}.")
    return conf


def read_settings_from_file(_: Optional[pydantic.BaseSettings]) -> Dict[str, Any]:
    for path in CONFIG_PATHS:
        if os.path.exists(path):
            with open(path, "r", encoding="UTF-8") as file:
                return json.load(file)

    if not SETTINGS_CREATE_NONEXISTENT:
        if SETTINGS_LOG_ERROR_FUNCTION:
            SETTINGS_LOG_ERROR_FUNCTION(
                "No config file found! Use the 'init' command to create a basic configuration file or "
                "use the 'auto' mode which does all the setup by environment variables automatically."
            )
        if SETTINGS_EXIT_ON_ERROR:
            sys.exit(1)
        return get_default_core_config(
            os.environ.get("DATABASE_CONNECTION", os.environ.get("DATABASE__CONNECTION", None))
        ).dict()

    else:
        conf = store_configuration()
        if SETTINGS_EXIT_ON_ERROR:
            sys.exit(1)
        return conf.dict()


def get_default_core_config(database_override: Optional[str] = None) -> config.CoreConfig:
    c = config.CoreConfig(
        general=config.GeneralConfig(),
        server=config.ServerConfig(),
        logging=config.LoggingConfig(),
        database=config.DatabaseConfig()
    )
    if database_override:
        c.database.connection = database_override
    return c


def get_default_config(_: Optional[pydantic.BaseSettings] = None) -> Dict[str, Any]:
    return get_default_core_config().dict()
