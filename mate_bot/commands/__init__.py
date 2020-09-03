#!/usr/bin/env python3

"""
MateBot collection of commands
"""


from .base import BaseCommand, BaseQuery

from .balance import BalanceCommand
from .bootstrap import StartCommand
from .communism import CommunismCommand, CommunismQuery, Communism
from .consume import ConsumeCommand, DrinkCommand, IceCommand, PizzaCommand, WaterCommand
from .data import DataCommand
from .history import HistoryCommand
from .pay import PayCommand, PayQuery, Pay
from .send import SendCommand


__all__ = [
    "BaseCommand",
    "BaseQuery",
    "BalanceCommand",
    "StartCommand",
    "CommunismCommand",
    "CommunismQuery",
    "Communism",
    "ConsumeCommand",
    "DrinkCommand",
    "IceCommand",
    "PizzaCommand",
    "WaterCommand",
    "DataCommand",
    "HistoryCommand",
    "PayCommand",
    "PayQuery",
    "Pay",
    "SendCommand"
]
