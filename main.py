#!/usr/bin/env python3

import asyncio
import logging

from nio import InviteEvent, RoomMessageText

from hopfenmatrix.api_wrapper import ApiWrapper

from mate_bot.config import config
#from mate_bot.state.dbhelper import BackendHelper
from mate_bot.commands.base import BaseCommand
from mate_bot.commands.help import HelpCommand
from mate_bot.commands.balance import BalanceCommand
from mate_bot.commands.start import StartCommand
from mate_bot.commands.zwegat import ZwegatCommand
from mate_bot.commands.consume import ConsumeCommand


async def main():
    '''
    BackendHelper.db_config = config["database"]
    BackendHelper.query_logger = logging.getLogger("database")
    BackendHelper.get_value("users")
    '''

    api = ApiWrapper(config=config)
    api.set_auto_join(allowed_rooms=[config.room])

    client = api.client
    client.add_event_callback(HelpCommand(api), RoomMessageText)
    client.add_event_callback(BalanceCommand(api), RoomMessageText)
    client.add_event_callback(StartCommand(api), RoomMessageText)
    client.add_event_callback(ZwegatCommand(api), RoomMessageText)
    for consumable in config.consumables:
        client.add_event_callback(ConsumeCommand(api, **consumable), RoomMessageText)

    await api.start_bot()


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
