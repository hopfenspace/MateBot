"""
MateBot collection of commands
"""

from mate_bot.config import config
from mate_bot.commands.registry import COMMANDS
from mate_bot.commands.balance import BalanceCommand
from mate_bot.commands.communism import CommunismCommand
from mate_bot.commands.data import DataCommand
from mate_bot.commands.help import HelpCommand
from mate_bot.commands.history import HistoryCommand
from mate_bot.commands.pay import PayCommand
from mate_bot.commands.send import SendCommand
from mate_bot.commands.start import StartCommand
from mate_bot.commands.blame import BlameCommand
from mate_bot.commands.vouch import VouchCommand
from mate_bot.commands.zwegat import ZwegatCommand
from mate_bot.commands.consume import ConsumeCommand


# Register all commands
COMMANDS.add(BalanceCommand())
COMMANDS.add(CommunismCommand())
COMMANDS.add(DataCommand())
COMMANDS.add(HelpCommand())
COMMANDS.add(HistoryCommand())
COMMANDS.add(PayCommand())
COMMANDS.add(SendCommand())
COMMANDS.add(StartCommand())
COMMANDS.add(BlameCommand())
COMMANDS.add(VouchCommand())
COMMANDS.add(ZwegatCommand())
for consumable in config["consumables"]:
    COMMANDS.add(ConsumeCommand(**consumable))
