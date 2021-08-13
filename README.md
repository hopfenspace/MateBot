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
   pip3 install -r requirements.txt
   ```
4. Execute the MateBot core once:
   ```shell
   python3 -m matebot_core
   ```
5. Edit the newly created config file `config.json`. Important parts
   are the server and database settings, but you may want to change
   the general or logging settings as well.

### Executing

Executing the MateBot REST API can simply be done by calling the module:
```shell
python3 -m matebot_core
```
Take a look at the built-in help page using `--help`.

### Creating a systemd service

On systemd-enabled systems, it's recommended to add a systemd service to
start the MateBot core API automatically. To do so, call the module with
the `--systemd` option, add a symlink to it, reload the systemd daemon
and finally enable the new service. All steps as an example below:

```shell
python3 -m matebot_core --systemd
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
