"""
MateBot configuration provider
"""

import os as _os
import json as _json


if _os.path.exists("config.json"):
    with open("config.json", "r") as f:
        config = _json.load(f)

elif _os.path.exists(_os.path.join("..", "config.json")):
    with open(_os.path.join("..", "config.json")) as f:
        config = _json.load(f)

else:
    raise ImportError("No configuration file found")
