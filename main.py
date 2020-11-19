#!/usr/bin/env python3

import asyncio
import logging

from hopfenmatrix.client import new_async_client
from hopfenmatrix.run import run

from mate_bot.config import config
from mate_bot.state.dbhelper import BackendHelper


async def main():
    BackendHelper.db_config = config["database"]
    BackendHelper.query_logger = logging.getLogger("database")
    BackendHelper.get_value("users")

    client = new_async_client(config)

    await run(client, config)


if __name__ == "__main__":
    asyncio.get_event_loop().run_until_complete(main())
