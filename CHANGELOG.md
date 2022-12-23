# MateBot core v0.6 (2022-12-24)

- **New feature** of a fully usable CLI to manage users and applications, which
  also solved the "first user problem" by being able to promote them manually
- **New feature** of the "auto mode", which can be used to bootstrap the MateBot
  core API in just a single command (mainly configured by environment variables)
- **Breaking change** by switching from SHA512-hashed passwords with multiple
  iterations to Argon2, which also fixed a GitHub security notice; however,
  this breaks the current login workflow for existing applications -- therefore,
  all applications must be re-created after this release has been applied (#122)
- **Notable change** by replacing the `GET /status` endpoint with the
  unauthenticated `GET /health` endpoint (#102)
- Added support for Docker (#119)
- Allow overwriting almost all config settings environment variables
- Extended the unittest suite to perform load tests and CLI tests as well
- Fixed three failing unittests (#118)

Merry Christmas :)

# MateBot core v0.5.4 (2022-12-11)

- **Notable change** by not exposing shared secrets via the API
- Allow overwriting certain config options via environment variables
- Fixed a lot of inconsistencies and bugs
- Updated the documentation
- Added a migration script to convert from the old database to the core API
  schema which is expected to work as long as no further migrations are required
- Handle `RuntimeError` as a valid exception to produce HTTP `400` responses
- Added support for Python 3.11
- Updated minimal dependencies
  - `alembic` to `1.8`
  - `fastapi` to `0.88`
  - `pydantic` to `1.10`, adding the extra dependency `dotenv` for `.env` files
  - `requests` to `2.27`
  - `uvicorn` to `0.20`

# MateBot core v0.5.3 (2022-09-14)

- **Important change** by adding a globally unique name attribute to the user
- **Changed endpoint** `POST /users` to require a unique username
- **New endpoint** `POST /users/setName` to change the username, if available
- **Notable change** by adding the user's name attribute to the
  schemas `Vote` and `CommunismUserBinding`
- Added a filter `username` to the users endpoint
- Updated the setup utility to accept a custom community name

# MateBot core v0.5.2 (2022-08-27)

- Changed project license from **GLPv3** to **AGPLv3**
- Added pagination to all relevant GET endpoints
- Require the `ìssuer` for voucher update requests
- Fixed logging and unittest bugs
- Added a filter `alias_application` to the users endpoint
- Fixed bug in `POST /aliases/delete` endpoint

# MateBot core v0.5.1 (2022-06-26)

- **Notable change** by dropping the Python version from `/status` endpoint
- **Notable change** by dropping defaults and optionals of the `APIError` model
- Added two new subcommands to the CLI for better application management
- Update FastAPI to version 0.78.0
- Fixed logging problems due to updates in `uvicorn` and updated it to v0.18
- Fixed warnings for endpoints not having explicit version annotations
- Added a logging filter to suppress multipart DEBUG logs by default

# MateBot core v0.5 (2022-06-19)

- Rebuild the callback functionality with event posting using `POST` including
  various useful details for the callback server with optional authentication,
  together with an event buffer to cache the most recent events for more speed
- **Breaking change** of various endpoints e.g. for the updates of the
  participation in communisms, sending money and consuming goods, dropping
  privileges or disabling users to make it more intuitive
- Rewrite the handling of membership polls with a new `variant` field
  to determine the type of poll, with the current options being
  `get_internal`, `get_permission`, `loose_internal` and `loose_permission`
- **Breaking change** by removed the unused endpoints `GET /ballots`,
  `GET /multitransactions`, `PUT /callbacks`, `PUT /aliases`,
  `DELETE /aliases`, `POST /users/setFlags` and `POST /users/setName`
- Replaced all `404` HTTP responses with `400` responses
- Accept user aliases combined with the application ID from
  the auth token as valid user specification
- Added an `issuer` field for various operations to enforce user
  permission checks on the API server instead of client applications
- Rewrote the API unittests to use subprocesses instead of threads to run the
  API server for better end-to-end tests and fixed various smaller issues
- Fixed a bug preventing general consumption
- Dropped the user's name attribute and its handling functionality
- Implemented the limitations of the config options `max_parallel_debtors`,
  `max_transaction_amount` and `max_simultaneous_consumption`
- Rewrote and extended some bigger parts of the sphinx documentation
- Fixed some problems with the database migrations on SQLite databases

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
