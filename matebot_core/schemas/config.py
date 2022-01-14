"""
Special schemas for the configuration file and its properties
"""

from typing import Dict

import pydantic


class GeneralConfig(pydantic.BaseModel):
    min_refund_approves: pydantic.PositiveInt = 2
    min_refund_disapproves: pydantic.PositiveInt = 2
    max_parallel_debtors: pydantic.PositiveInt = 3
    max_simultaneous_consumption: pydantic.conint(gt=2) = 20
    max_transaction_amount: pydantic.conint(gt=100) = 50000


class ServerConfig(pydantic.BaseModel):
    host: str = "127.0.0.1"
    port: pydantic.conint(gt=0, lt=65536) = 8000


class DatabaseConfig(pydantic.BaseModel):
    connection: str = "sqlite://"
    debug_sql: bool = False


class LoggingConfig(pydantic.BaseModel):
    version: pydantic.conint(ge=1, le=1) = 1
    disable_existing_loggers: bool = False
    incremental: bool = False
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
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": "%(asctime)s %(client_addr)s - \"%(request_line)s\" %(status_code)s"
        }
    }
    loggers: Dict[str, dict] = {}
    handlers: Dict[str, Dict[str, str]] = {
        "default": {
            "level": "INFO",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
            "formatter": "default"
        },
        "file": {
            "level": "INFO",
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
    database: DatabaseConfig
    logging: LoggingConfig
