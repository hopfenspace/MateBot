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
