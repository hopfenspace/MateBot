"""
Special schemas for the configuration file and its properties
"""

from typing import Dict, List, Optional, Union

import pydantic

from .bases import Consumable


class GeneralConfig(pydantic.BaseModel):
    min_refund_approves: pydantic.PositiveInt = 2
    min_refund_disapproves: pydantic.PositiveInt = 2
    min_membership_approves: pydantic.PositiveInt = 2
    min_membership_disapproves: pydantic.PositiveInt = 2
    max_parallel_debtors: pydantic.PositiveInt = 10
    max_simultaneous_consumption: pydantic.conint(gt=2) = 100
    max_transaction_amount: pydantic.conint(gt=100) = 50000


class ServerConfig(pydantic.BaseModel):
    host: str = "127.0.0.1"
    port: pydantic.conint(gt=0, lt=65536) = 8000
    password_iterations: int = 2**20
    public_base_url: Optional[pydantic.HttpUrl] = None


class DatabaseConfig(pydantic.BaseModel):
    connection: str = "sqlite://"
    debug_sql: bool = False


class LoggingConfig(pydantic.BaseModel):
    version: pydantic.conint(ge=1, le=1) = 1
    disable_existing_loggers: bool = False
    incremental: bool = False
    filters: Dict[str, Dict[str, Union[str, list]]] = {
        "multipart_no_debug": {
            "()": "matebot_core.misc.logger.NoDebugFilter",
            "name": "multipart.multipart"
        }
    }
    formatters: Dict[str, Dict[str, str]] = {
        "default": {
            "style": "{",
            "format": "{asctime}: MateBot {process}: [{levelname}] {name}: {message}",
            "datefmt": "%d.%m.%Y %H:%M:%S"
        },
        "file": {
            "style": "{",
            "format": "{asctime} ({process}): [{levelname}] {name}: {message}",
            "datefmt": "%d.%m.%Y %H:%M"
        },
        "access": {
            "()": "uvicorn._logging.AccessFormatter",
            "fmt": "%(asctime)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"
        }
    }
    loggers: Dict[str, dict] = {}
    handlers: Dict[str, Dict[str, Union[str, list]]] = {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default"
        },
        "file": {
            "level": "DEBUG",
            "class": "logging.FileHandler",
            "filename": "./matebot.log",
            "formatter": "file"
        },
        "access": {
            "level": "INFO",
            "class": "logging.FileHandler",
            "filename": "./access.log",
            "formatter": "access"
        }
    }
    root: dict = {
        "level": "INFO",
        "handlers": ["default", "file"]
    }


class CoreConfig(pydantic.BaseModel):
    general: GeneralConfig
    server: ServerConfig
    consumables: List[Consumable] = []
    database: DatabaseConfig
    logging: LoggingConfig

    @pydantic.validator("consumables")
    def enforce_consumable_constraints(
            value: List[Consumable]  # noqa
    ):
        if len({v.name.lower() for v in value}) != len(value):
            raise ValueError("Field 'name' must be unique")
        return value
