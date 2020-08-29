#!/usr/bin/env python3


class BaseStateException(Exception):
    """
    Base class for all project-wide exceptions
    """


class DesignViolation(BaseStateException):
    """
    Exception when a situation is not intended by design while being a valid state
    """
