import json
from typing import Dict, List

from .user import MateBotUser


def load(fpath: str = "state.json") -> Dict[str, MateBotUser]:
    def dict_to_user(dct: Dict) -> MateBotUser:
        return MateBotUser(**dct)

    with open(fpath, "r") as fd:
        return dict((key, dict_to_user(dct)) for key, dct in json.load(fd).items())


def save(users: Dict[str, MateBotUser], fpath: str = "state.json"):
    def user_to_dict(user: MateBotUser) -> Dict:
        return user.__dict__

    with open(fpath, "w") as fd:
        json.dump(dict(((key, user_to_dict(user)) for key, user in users.items())), fd)
