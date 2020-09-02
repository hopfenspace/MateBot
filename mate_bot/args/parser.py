#!/usr/bin/env python3

"""
MateBot argument parsing helper library
"""

import argparse


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
        raise ParsingError(message)


class ParsingError(Exception):
    """
    Exception raised when the parser throws an error

    This is likely to happen when a user messes up the syntax of a
    particular command. Instead of exiting the program, this exception
    will be raised. You may use it's string representation to gain
    additional information about what went wrong. This allows a user
    to correct its command, in case this caused the parser to fail.
    """

    pass
