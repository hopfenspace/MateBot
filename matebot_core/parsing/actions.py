"""
MateBot parser's actions class defining arguments.
"""

from typing import Optional
import typing

from mate_bot.err import ParsingError
from mate_bot.parsing.util import Namespace, Representable


class Action(Representable):
    """
    Information about how to convert command line strings to Python objects.

    Action objects are used by an CommandParser to represent the information
    needed to parse a single argument from one or more strings from the
    command line. The keyword arguments to the Action constructor are also
    all attributes of Action instances.

    :param dest: The name of the attribute to hold the created object(s)
    :type dest: str

    :param nargs: The number of command-line arguments that should be
                  consumed. By default, one argument will be consumed and a single
                  value will be produced.  Other values include:

                  * ``N`` (an integer) consumes N arguments (and produces a list)
                  * ``'?'`` consumes zero or one arguments
                  * ``'*'`` consumes zero or more arguments (and produces a list)
                  * ``'+'`` consumes one or more arguments (and produces a list)

                  Note that the difference between the default and ``nargs=1`` is that
                  with the default, a single value will be produced, while with
                  ``nargs=1``, a list containing a single value will be produced.
    :type nargs: Union[str, int]

    :param default: The value to be produced if the option is not specified.
    :type default: Any

    :param type: A callable that accepts a single string argument,
                 and returns the converted value. See :ref:`mate_bot.parsing.types` for examples.
    :type type: Callable

    :param choices: A tuple of values that should be allowed.
    :type choices: Tuple[str]

    :param metavar: The name to be used in the help string.
                    If ``None``, the ``dest`` value will be used as the name.
    :type metavar: str
    """

    def __init__(self,
                 dest: str,
                 nargs: Optional[typing.Union[int, str]] = None,
                 default: Optional[typing.Any] = None,
                 type: Optional[typing.Callable] = str,
                 choices: Optional[typing.Tuple[str]] = None,
                 metavar: Optional[str] = None):
        """"""
        self.dest = dest
        self.nargs = nargs
        self.default = default
        self.type = type
        self.choices = choices
        self.metavar = metavar

    def _get_kwargs(self):
        names = [
            'dest',
            'nargs',
            'default',
            'type',
            'choices',
            'metavar',
        ]
        return [(name, getattr(self, name)) for name in names]

    def __call__(self, namespace: Namespace, values: typing.Union[typing.Any, typing.List[typing.Any]]):
        """
        Put the parsed values in the namespace object.

        This is a abstract method and should be overwritten to create specific actions.
        It may process the values in some ways and should put them into the namespace under ``dest``.

        :param namespace: Namespace object to put values into
        :type namespace: Namespace
        :param values: The converted value or values
        :type values: Union[Any, List[Any]]
        :raises NotImplementedError: when called
        """
        raise NotImplementedError('.__call__() not defined')

    @property
    def min_args(self) -> int:
        """
        Get the minimum amount of arguments this action can take.

        :return: minimum amount of arguments this action can take
        :rtype: int
        """
        if isinstance(self.nargs, int):
            return self.nargs
        elif self.nargs in ["?", "*"]:
            return 0
        elif self.nargs in ["+", None]:
            return 1
        else:
            raise RuntimeError(f"invalid nargs value: {repr(self.nargs)}")

    @property
    def max_args(self) -> typing.Union[int, float]:
        """
        Get the maximum amount of arguments this action can take.

        :return: maximum amount of arguments this action can take
        :rtype: int or +- infinity (float)
        """
        if isinstance(self.nargs, int):
            return self.nargs
        elif self.nargs in ["?", None]:
            return 1
        elif self.nargs in ["+", "*"]:
            return float("inf")
        else:
            raise RuntimeError(f"invalid nargs value: {repr(self.nargs)}")


class StoreAction(Action):
    """
    This action just stores whatever the parser gives it.
    """

    def __call__(self, namespace: Namespace, values: typing.Union[typing.Any, typing.List[typing.Any]]):
        """
        Store values as given in the namespace object.

        :param namespace: Namespace object to put values into
        :type namespace: Namespace
        :param values: The converted value or values
        :type values: Union[Any, List[Any]]
        """
        setattr(namespace, self.dest, values)


class JoinAction(Action):
    """
    This action takes strings and joins them with spaces.

    When given a limit as keyword argument,
    it also checks if the resulting message exceeds given limit.

    :param limit: max number of characters or None to disable check
    :type limit: int
    """

    def __init__(self,
                 dest: str,
                 nargs: Optional[typing.Union[int, str]] = None,
                 default: Optional[typing.Any] = None,
                 type: Optional[typing.Callable] = str,
                 choices: Optional[typing.Tuple[str]] = None,
                 metavar: Optional[str] = None,
                 limit: Optional[int] = 255):
        """"""
        super(JoinAction, self).__init__(dest, nargs, default, type, choices, metavar)
        self.limit = limit

    def __call__(self, namespace: Namespace, values: typing.Union[typing.Any, typing.List[typing.Any]]):
        """
        Call ``str.join`` on the values before storing them.

        This actions can only work with strings (``type=str``)
        and needs them in a list (``nargs="*"``, ``nargs="+"`` or ``nargs`` is an integer)

        :param namespace: Namespace object to put values into
        :type namespace: Namespace
        :param values: strings to join
        :type values: List[str]
        """

        value = " ".join(values)
        if self.limit is not None and self.limit < len(value):
            raise ParsingError(f"Message too long (max {self.limit} characters)")
        else:
            setattr(namespace, self.dest, value)
