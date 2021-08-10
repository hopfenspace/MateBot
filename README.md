# MateBot core REST API

The API provided in this package allows clients to handle a diverse user base,
where every user has any number of associated aliases but one shared balance.
It can be sent to other users, shared in bills or refunded by the community
by a community ballot, where every user has the equal privileges and voting
weight. Additionally, the API provides endpoints to easily consume any
amount of predefined but modifiable consumables with different stocks.

## Productive installation

### Pre-requirements

- Python >= 3.7
- pip >= 18

### Installation, configuration, execution

1. Create a new directory which should be your working directory.
2. Install the basic version or install the full version at your choice:
   ```shell
   python3 -m venv venv
   venv/bin/python3 -m pip install matebot_core
   ```
   or
   ```shell
   python3 -m venv venv
   venv/bin/python3 -m pip install matebot_core[full]
   ```
   The difference lies in some additional modules providing some
   optional features, e.g. static files without CDN for the docs.
3. Execute it once to create the configuration file there:
   ```shell
   python3 -m matebot_core
   ```
4. Edit the newly created config file `config.json`. Important parts
   are the server and database settings, but you may want to change
   the general or logging settings as well.
5. Make sure that you have required bindings (modules) for the selected
   database technology and that it's supported by SQLAlchemy. If you're
   not sure, stick with SQLite first and change it later on.
6. Executing the MateBot REST API can simply be done by calling the module:
   ```shell
   python3 -m matebot_core
   ```
   Take a look at the built-in help page using `--help`.

## Documentation

See the `docs/` folder or [our deployed documentation](https://docs.hopfenspace.org/matebot).

**Note that the documentation is currently outdated!**

## License

See [GPLv3 license](LICENSE).
