"""
MateBot configuration provider
"""

import os
import json
import typing
import logging as _logging


class ReadOnlyDict(dict):
    """
    Read-only variant of a dictionary that also supports access via attributes
    """

    def __setitem__(self, key, value):
        _logging.getLogger("config").warning(
            f"Ignoring write access to the config ({key}:{value})"
        )

    def __setattr__(self, key, value):
        self[key] = value

    def __getattr__(self, item):
        return self[item]


class Configuration:
    """
    Configuration storage via its property attribute :attr:`data`
    """

    _content: str
    _data: typing.Optional[ReadOnlyDict]
    _path: str

    def __init__(self, config_file: str):
        self._path = config_file
        with open(self._path, "r") as f:
            self._content = f.read()
        self._data = None

    def validate(self) -> bool:
        return True  # TODO

    @property
    def data(self) -> typing.Optional[ReadOnlyDict]:
        """
        Get the full config data as read-only dictionary
        """

        if self._data is None:
            if not self.validate():
                raise ValueError("Config validation was not successful")
            self._data = ReadOnlyDict(**json.loads(self._content), _path=self._path)
        return self._data


for check in [
    "config.json",
    os.path.join("..", "config.json")
]:
    if os.path.exists(check):
        configuration = Configuration(check)
        config = configuration.data
        break
else:
    raise ImportError("No configuration file found")
