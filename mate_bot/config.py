"""
MateBot configuration provider
"""

import os as _os
import json as _json
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


if _os.path.exists("config.json"):
    with open("config.json", "r") as f:
        config = _json.load(f)

elif _os.path.exists(_os.path.join("..", "config.json")):
    with open(_os.path.join("..", "config.json")) as f:
        config = _json.load(f)

else:
    raise ImportError("No configuration file found")
