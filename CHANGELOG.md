# MateBot core v0.4.2 (2022-04-29)

- Cleaned up some modules
- Fixed problems of occupied ports in unittests

# MateBot core v0.4.1 (2022-04-27)

Security release updating the `ujson` dependency to `>5.0`.

# MateBot core v0.4 (2022-03-02)

This release can be considered stable and almost feature-complete.

- Changed the API design from a pure REST-like to a verb-based API for
  most functionality, the only exceptions being `aliases` and `callbacks`
- Implemented a filter-like search functionality on almost all GET endpoints
- Consumables are now set up in the config and not in the database,
  manipulation isn't possible via the API anymore
- Applications can't be changed via the API now (use the CLI instead)
- Improved the request validation error handling & dropped HTTP `422` responses
- [Alembic](https://alembic.sqlalchemy.org) was added to the
  project to store future database migrations
- Reworked the ballot and vote handling with new database models
- Improved the CLI functionality of the module
- Fixed various problems with unittests and GitHub CI

# MateBot core v0.3 (2022-02-01)

Re-implementation as [FastAPI](https://fastapi.tiangolo.com)-based
HTTP microservice as a full REST API. This release included the use of
SQLAlchemy as database ORM, authentication using JWT and versioned
endpoints starting with `/v1`. The API as well as the database models
are also checked using Python unittests that are run using GitHub CI.

# MateBot v0.2 (2020-12-11)

Re-implementation as new Telegram bot with some more commands, a vouching
system cross-chat message synchronization and distinguishing internal from
external users for a simple permission system. This bot used an SQL database
as its data backend with a hand-made SQL wrapper (SQLite and MySQL are
supported). This release also included a full sphinx documentation of the bot.

# MateBot v0.1 (2020-07-23)

First implementation as a rudimentary Telegram bot that provides the core
commands (`balance`, `send`, `pay`, `communism`, `history`, `zwegat` and
those for consumptions) with a JSON-file as storage backend.
