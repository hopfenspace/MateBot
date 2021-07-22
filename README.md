# MateBot

REST API with Telegram Bot as frontend that sells Mate, ice
cream and pizza and allows you to share bills or get refunds.

## Installation

### Requirements

- Python >= 3.7.3
- [python-telegram-bot](https://pypi.org/project/python-telegram-bot/)
- [tzlocal](https://pypi.org/project/tzlocal/)
- [PyMySQL](https://pypi.org/project/PyMySQL/)
- [FastAPI](https://pypi.org/project/FastAPI/)

You may have [mysqlclient](https://pypi.org/project/mysqlclient/) installed
on your machine. In case it's available, we prefer it over
[PyMySQL](https://pypi.org/project/PyMySQL/). However, it requires installation
of OS-specific libraries which the pure-Python implementation does not.
Therefore, there's the requirement for the pure-Python library while
the other one could be used too.

## Documentation

See `docs` folder or [our deployed documentation](https://docs.hopfenspace.org/matebot).

## License

See [license](LICENSE).
