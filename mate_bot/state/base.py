"""
MateBot's absolute base classes as minimal dependency
"""

import typing
import logging


class LoggerBase:
    """
    Base class for anything that has to write something to the logs

    This class is useful when the logging framework is configured after
    importing the specific module, because a global ``logger`` would
    be configured during importing. But using this class allows the
    logger to be configured upon initialization of the used object.

    Classes that inherit from this class should call ``super().__init__``
    once, optionally specifying the logger name as ``logger_name``.
    Afterwards, subclasses and its objects can use ``self.logger`` to
    send logs to the named logger object of the logging framework. When
    you specify an empty string as ``logger_name``, the root logger will
    be used. When you specify ``None``, the class name will be used.

    :param logger_name: name of the logger to use (defaults to class name)
    :type logger_name: typing.Optional[str]
    """

    def __init__(self, logger_name: typing.Optional[str] = None):
        if logger_name is None:
            logger_name = type(self).__name__
        if logger_name == "":
            logger_name = None
        self.logger = logging.getLogger(logger_name)
