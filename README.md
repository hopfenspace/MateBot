# MateBot core REST API

<p align="center">
   <img width="120px" src="https://raw.githubusercontent.com/hopfenspace/MateBot/dev/static/img/matebot_alpha_1024.png" alt="MateBot core REST API logo" />
</p>

The API provided in this package allows clients to handle a diverse user base,
where every user has any number of associated aliases but one shared balance.
It can be sent to other users, shared in bills or refunded by the community
by a community poll, where every user has the equal privileges and voting
weight. Additionally, the API provides endpoints to easily consume any
amount of consumables and vouch for other users in case of high debts.

## Installation

### Pre-requirements

- Python >= 3.7
- pip >= 18

### Installation & configuration

1. Clone this repository into your project directory.
2. Set up a new virtual environment:
   ```shell
   python3 -m venv venv
   ```
   You may need to install adequate system packages first
   (e.g. `apt install python3-venv` on Debian-like system).
3. Install the required packages:
   ```shell
   venv/bin/pip3 install -r requirements.txt
   ```
4. Initialize the MateBot core data once (`--help` to show the options first):
   ```shell
   venv/bin/python3 -m matebot_core init --help
   ```
5. Edit the newly created config file `config.json`. Important parts
   are the server and database settings, but you may want to change
   the general or logging settings as well. You should always use
   a persistent database, even if it's a sqlite database, since the
   in-memory sqlite database is currently not working properly.
6. Create new application accounts to authenticate against the API
   (use `--help` to show the options); the password may either be given
   via the `--password` option or interactively via standard input:
   ```shell
   venv/bin/python3 -m matebot_core add-app --app <APPLICATION NAME>
   ```

### Executing

Executing the MateBot REST API can simply be done by calling the module:
```shell
python3 -m matebot_core run
```
Take a look at the built-in help page using `--help`.

### Upgrading

This project uses [alembic](https://alembic.sqlalchemy.org) to handle database
migrations. Ideally, the upgrade procedure would contain those steps:

1. Read the release notes, because they may contain additional information.
2. Shutdown the web server.
3. Make a backup of the database.
4. Pull the new version of the project.
5. Run `venv/bin/alembic upgrade head`.
6. Start the web server again.

### Creating a systemd service

On systemd-enabled systems, it's recommended to add a systemd service to
start the MateBot core API automatically. To do so, call the module with
the `systemd` command, add a symlink to it, reload the systemd daemon
and finally enable the new service. All steps as an example below:

```shell
venv/bin/python3 -m matebot_core systemd
sudo ln -vrs matebot_core.service /lib/systemd/system/matebot_core.service
sudo systemctl daemon-reload
sudo systemctl enable matebot_core
sudo systemctl start matebot_core
```

## Documentation

See the `docs/` folder or [our deployed documentation](https://docs.hopfenspace.org/matebot).

**Note that the documentation is currently outdated!**

## License

See [GPLv3 license](LICENSE).
