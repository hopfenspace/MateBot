"""
MateBot project-wide exception classes
"""

import logging as _logging


_logger = _logging.getLogger("error")


class MateBotException(Exception):
    """
    Base class for all project-wide exceptions
    """


class DesignViolation(MateBotException):
    """
    Exception when a situation is not intended by design while being a valid state

    This exception is likely to occur when a database operation
    fails due to specific checks. It ensures e.g. that no
    second community user exists in a database or that a user
    is participating in a collective operation at most one time.
    """


class ParsingError(MateBotException):
    """
    Exception raised when the argument parser throws an error

    This is likely to happen when a user messes up the syntax of a
    particular command. Instead of exiting the program, this exception
    will be raised. You may use it's string representation to gain
    additional information about what went wrong. This allows a user
    to correct its command, in case this caused the parser to fail.
    """


class CallbackError(MateBotException):
    """
    Exception raised when parsing or handling callback data throws an error

    This may occur when the callback data does not hold enough information
    to fulfill the desired operation, is of a wrong format or points to
    invalid data (e.g. a payment's callback data points to a communism).
    This type of exception should not happen as it implies serious problems.
    """
