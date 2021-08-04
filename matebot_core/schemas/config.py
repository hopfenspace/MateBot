"""
Special schemas for the configuration file and its properties
"""

from typing import Dict

import pydantic


class GeneralConfig(pydantic.BaseModel):
    max_amount: pydantic.conint(gt=100) = 10000
    max_consume: pydantic.conint(gt=2) = 10


class CommunityConfig(pydantic.BaseModel):
    payment_consent: pydantic.PositiveInt = 2
    payment_denial: pydantic.PositiveInt = 2
    max_vouched: pydantic.PositiveInt = 3


class LoggingConfig(pydantic.BaseModel):
    version: pydantic.conint(ge=1, le=1) = 1
    disable_existing_loggers: bool = True
    incremental: bool = False
    formatters: Dict[str, dict] = {}
    loggers: Dict[str, dict] = {}
    handlers: Dict[str, dict] = {
        "console": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        }
    }
    root: dict = {
        "level": "DEBUG",
        "handlers": ["console"]
    }


class DatabaseConfig(pydantic.BaseModel):
    connection: str = "sqlite://"
    echo: bool = True


class CoreConfig(pydantic.BaseModel):
    general: GeneralConfig
    community: CommunityConfig
    logging: LoggingConfig
    database: DatabaseConfig
