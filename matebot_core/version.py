"""
MateBot core version info
"""

from collections import namedtuple as _namedtuple

__version__ = "0.3.0"

_VersionInfo = _namedtuple("VersionInfo", ("major", "minor", "micro"))
_VersionInfo.__doc__ = "Tuple containing version information"

PROJECT_VERSION: str = __version__
PROJECT_VERSION_INFO: _VersionInfo = _VersionInfo(*(PROJECT_VERSION.split(".")))

API_VERSION: str = "0.3"
