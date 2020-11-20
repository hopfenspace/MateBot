#!/usr/bin/env python3

import asyncio

from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.config import config
from mate_bot.commands.help import HelpCommand
from mate_bot.commands.balance import BalanceCommand
from mate_bot.commands.start import StartCommand
from mate_bot.commands.zwegat import ZwegatCommand
from mate_bot.commands.consume import ConsumeCommand
from mate_bot.commands.data import DataCommand
from mate_bot.commands.history import HistoryCommand


async def main():
    api = ApiWrapper(config=config)
    api.set_auto_join(allowed_rooms=[config.room])

    api.register_command(HelpCommand(), ["help"])
    api.register_command(BalanceCommand(), ["balance"])
    api.register_command(StartCommand(), ["start"])
    api.register_command(ZwegatCommand(), ["zwegat"])
    api.register_command(DataCommand(), ["data"])
    api.register_command(HistoryCommand(), ["history"])
    for consumable in config.consumables:
        api.register_command(ConsumeCommand(**consumable), [consumable["name"]])

    await api.start_bot()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
