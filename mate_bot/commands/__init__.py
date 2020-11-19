"""
MateBot collection of command executors
"""

'''
from mate_bot.commands.blame import BlameCommand
from mate_bot.commands.communism import CommunismCommand, CommunismCallbackQuery
from mate_bot.commands.data import DataCommand
from mate_bot.commands.forward import ForwardInlineQuery, ForwardInlineResult
from mate_bot.commands.history import HistoryCommand
from mate_bot.commands.pay import PayCommand, PayCallbackQuery
from mate_bot.commands.send import SendCommand, SendCallbackQuery
from mate_bot.commands.start import StartCommand
from mate_bot.commands.vouch import VouchCommand, VouchCallbackQuery


# In order to register all executors in the registry, we just
# have to create an object of their corresponding class. The
# constructors of the base classes care about adding the
# specific executor object to the correct registry pool.

BlameCommand()
CommunismCommand()
DataCommand()
HistoryCommand()
PayCommand()
SendCommand()
StartCommand()
VouchCommand()

CommunismCallbackQuery()
PayCallbackQuery()
SendCallbackQuery()
VouchCallbackQuery()

ForwardInlineQuery(r"^\d+(\s?\S?)*")
HelpInlineQuery(r"")

ForwardInlineResult(r"^forward-\d+-\d+-\d+")
'''
