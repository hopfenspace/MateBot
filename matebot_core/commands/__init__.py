"""
MateBot collection of command executors
"""

from matebot_core.config import config
from matebot_core.commands.balance import BalanceCommand
from matebot_core.commands.blame import BlameCommand
from matebot_core.commands.communism import CommunismCommand, CommunismCallbackQuery
from matebot_core.commands.data import DataCommand
from matebot_core.commands.forward import ForwardInlineQuery, ForwardInlineResult
from matebot_core.commands.help import HelpCommand, HelpInlineQuery
from matebot_core.commands.history import HistoryCommand
from matebot_core.commands.pay import PayCommand, PayCallbackQuery
from matebot_core.commands.send import SendCommand, SendCallbackQuery
from matebot_core.commands.start import StartCommand
from matebot_core.commands.vouch import VouchCommand, VouchCallbackQuery
from matebot_core.commands.zwegat import ZwegatCommand
from matebot_core.commands.consume import ConsumeCommand


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
