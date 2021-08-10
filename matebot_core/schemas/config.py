"""
Special schemas for the configuration file and its properties
"""

from typing import Dict

import pydantic


class GeneralConfig(pydantic.BaseModel):
    max_amount: pydantic.conint(gt=100) = 10000
    max_consume: pydantic.conint(gt=2) = 10
    payment_consent: pydantic.PositiveInt = 2
    payment_denial: pydantic.PositiveInt = 2
    max_vouched: pydantic.PositiveInt = 3


class ServerConfig(pydantic.BaseModel):
    host: str = "127.0.0.1"
    port: pydantic.conint(gt=0, lt=65536) = 8000


class DatabaseConfig(pydantic.BaseModel):
    connection: str = "sqlite://"
    echo: bool = True


class LoggingConfig(pydantic.BaseModel):
    version: pydantic.conint(ge=1, le=1) = 1
    disable_existing_loggers: bool = True
    incremental: bool = False
    formatters: Dict[str, Dict[str, str]] = {
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
        }
    }
    loggers: Dict[str, dict] = {
        "uvicorn.access": {
            "handlers": ["access"]
        }
    }
    handlers: Dict[str, Dict[str, str]] = {
        "default": {
            "level": "DEBUG",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout"
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        }
    }
    root: dict = {
        "level": "DEBUG",
        "handlers": ["default"]
    }


class CoreConfig(pydantic.BaseModel):
    general: GeneralConfig
    server: ServerConfig
    database: DatabaseConfig
    logging: LoggingConfig
