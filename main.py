#!/usr/bin/env python3

import asyncio
import logging

from nio import InviteEvent, RoomMessageText

from hopfenmatrix.client import new_async_client
from hopfenmatrix.run import run
from hopfenmatrix.callbacks import apply_filter, auto_join, allowed_rooms

from mate_bot.config import config
from mate_bot.state.dbhelper import BackendHelper
from mate_bot.commands.base import BaseCommand


async def main():
    BackendHelper.db_config = config["database"]
    BackendHelper.query_logger = logging.getLogger("database")
    BackendHelper.get_value("users")

    client = new_async_client(config)
    client.add_event_callback(apply_filter(auto_join(client), allowed_rooms(config.room)), InviteEvent)
    client.add_event_callback(BaseCommand(client, "test", "I'm a test command"), RoomMessageText)

    await run(client, config)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
