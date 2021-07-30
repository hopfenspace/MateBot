"""
MateBot schema definitions

Any schema has a base name and any of the following extended names:
 * ``Creation`` to create a new instance of that schema
 * ``Update`` to replace an existing instance of that schema
 * ``Patch`` to modify an existing instance of that schema
For example, there are three classes to represent users:
``User``, ``UserCreation`` and ``UserUpdate``

The difference between an update and a patch is the fact that
a patch has optional fields only (except for the ID of the
object which should be affected by the proposed changes). Any
field of the original model that should not be affected by some
proposed change can therefore just be omitted with a patch.
"""

from .bases import *
from .errors import *
from .extra import *
from .groups import *
