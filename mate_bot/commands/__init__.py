"""
MateBot collection of command executors
"""

from mate_bot.config import config
from mate_bot.commands.balance import BalanceCommand
from mate_bot.commands.blame import BlameCommand
from mate_bot.commands.communism import CommunismCommand, CommunismCallbackQuery
from mate_bot.commands.data import DataCommand
from mate_bot.commands.forward import ForwardInlineQuery, ForwardInlineResult
from mate_bot.commands.help import HelpCommand, HelpInlineQuery
from mate_bot.commands.history import HistoryCommand
from mate_bot.commands.pay import PayCommand, PayCallbackQuery
from mate_bot.commands.send import SendCommand, SendCallbackQuery
from mate_bot.commands.start import StartCommand
from mate_bot.commands.vouch import VouchCommand, VouchCallbackQuery
from mate_bot.commands.zwegat import ZwegatCommand
from mate_bot.commands.consume import ConsumeCommand


# In order to register all executors in the registry, we just
# have to create an object of their corresponding class. The
# constructors of the base classes care about adding the
# specific executor object to the correct registry pool.

BalanceCommand()
BlameCommand()
CommunismCommand()
DataCommand()
HelpCommand()
HistoryCommand()
PayCommand()
SendCommand()
StartCommand()
VouchCommand()
ZwegatCommand()

for consumable in config["consumables"]:
    ConsumeCommand(**consumable)

CommunismCallbackQuery()
PayCallbackQuery()
SendCallbackQuery()
VouchCallbackQuery()

ForwardInlineQuery(r"^\d+(\s?\S?)*")
HelpInlineQuery(r"")

ForwardInlineResult(r"^forward-\d+-\d+-\d+")
