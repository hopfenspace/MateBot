#!/usr/bin/env python3

"""
MateBot argument parsing helper library
"""

import argparse

import err


class NonExitingParser(argparse.ArgumentParser):
    """
    Argument parser that does not exit the program

    The ArgumentParser of the `argparse` module would exit the program
    when an error occurs. This is fine in the context of shells where each
    command is a stand-alone program and the program should exit when it
    doesn't understand what to do. But this is a bot handling multiple
    commands. It can't just stop when a user messes up the syntax.
    Therefore, this class overwrites the .error() and .exit() methods
    of the original `ArgumentParser` class from the `argparse` module.
    """

    def exit(self, status: int = 0, message: str = None) -> None:
        raise RuntimeError("The parser for \"{}\" tried to exit".format(self.prog))

    def error(self, message: str) -> None:
        raise err.ParsingError(message, self.format_usage())
