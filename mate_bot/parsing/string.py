from typing import Optional

from telegram import MessageEntity


class EntityString(str):
    """
    Extends str to add a telegram's MessageEntity in the constructor

    A CommandParser hands these objects as parameters for "type" functions.
    This object is a string so functions like `int` which expect a single string can still be used,
    while other function can access the entity if they need it.
    """

    def __new__(cls, string: str, _: Optional[MessageEntity] = None) -> "EntityString":
        return str.__new__(cls, string)

    def __init__(self, _: str, entity: Optional[MessageEntity] = None):
        super(EntityString, self).__init__()
        self.entity = entity

    def __repr__(self):
        return f"{self.__class__.__name__}('{self}', entity={self.entity})"
