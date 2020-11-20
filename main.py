#!/usr/bin/env python3

import asyncio
from typing import List

from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.config import config
from mate_bot.commands.base import BaseCommand
from mate_bot.commands.help import HelpCommand
from mate_bot.commands.balance import BalanceCommand
from mate_bot.commands.zwegat import ZwegatCommand
from mate_bot.commands.consume import ConsumeCommand
from mate_bot.commands.data import DataCommand
from mate_bot.commands.history import HistoryCommand
from mate_bot.commands.blame import BlameCommand


async def main():
    api = ApiWrapper(config=config)
    api.set_auto_join(allowed_rooms=[config.room])

    def register_command(cmd: BaseCommand, aliases: List[str] = None):
        if aliases is None:
            api.register_command(cmd, [cmd.name])
        else:
            api.register_command(cmd, [cmd.name] + aliases)

    register_command(HelpCommand())
    register_command(BalanceCommand())
    register_command(ZwegatCommand())
    register_command(DataCommand())
    register_command(HistoryCommand())
    register_command(BlameCommand())
    for consumable in config.consumables:
        register_command(ConsumeCommand(**consumable))

    await api.start_bot()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
