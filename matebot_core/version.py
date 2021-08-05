"""
MateBot core version info
"""

import collections as _collections
from typing import Tuple as _Tuple

__version__ = "0.3.0"

_ProjectVersion = _collections.namedtuple("_ProjectVersion", ("major", "minor", "micro"))
_ProjectVersion.__doc__ = "Tuple defining the project version"

PROJECT_VERSION: str = __version__
PROJECT_VERSION_INFO: _Tuple[int, int, int] = _ProjectVersion(*(PROJECT_VERSION.split(".")))

API_VERSION: str = "0.3"
