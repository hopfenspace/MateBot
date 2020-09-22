import typing

from mate_bot.commands.base import BaseCommand


class CommandRegistry:

    def __init__(self):
        self._commands = {}

    @property
    def commands_as_list(self) -> typing.List[BaseCommand]:
        return list(self._commands.values())

    @property
    def commands_as_dict(self) -> typing.Dict[str, BaseCommand]:
        return dict(self._commands)

    def add(self, cmd: BaseCommand):
        if cmd.name in self._commands:
            raise ValueError(f"command {cmd.name} is already in registry")
        else:
            self._commands[cmd.name] = cmd

    def get(self, name: str) -> BaseCommand:
        return self._commands[name]


COMMANDS = CommandRegistry()
