#!/usr/bin/env python3

import argparse


class NonExitingParser(argparse.ArgumentParser):
    """
    A NonExitingParser, as the name suggests, is an ArgumentParser which does not exit the whole program.

    An argparse's ArgumentParser would exit the program when an error occurs. This is fine in the context of
    shells where each command is its own program and the program should exit when it doesn't understand what
    to do. But this is a bot handling multiple commands. It can't just stop when a user messes up the syntax.

    It simply extends the ArgumentParser from the argparse module and overwrites the error and exit methods.
    """

    def exit(self, status: int = 0, message: str = None) -> None:
        raise RuntimeError("The parser for \"{}\" tried to exit".format(self.prog))

    def error(self, message: str) -> None:
        raise ParsingError(message)


class ParsingError(Exception):
    """
    The exception raised when the parser has an error (when argparse would just have exited).
    """
    pass
