"""
MateBot parser's actions class defining arguments
"""

import typing

from mate_bot.parsing.util import Namespace, Representable


class Action(Representable):
    """
    Information about how to convert command line strings to Python objects.

    Action objects are used by an CommandParser to represent the information
    needed to parse a single argument from one or more strings from the
    command line. The keyword arguments to the Action constructor are also
    all attributes of Action instances.

    Keyword Arguments:

        - dest -- The name of the attribute to hold the created object(s)

        - nargs -- The number of command-line arguments that should be
            consumed. By default, one argument will be consumed and a single
            value will be produced.  Other values include:
                - N (an integer) consumes N arguments (and produces a list)
                - '?' consumes zero or one arguments
                - '*' consumes zero or more arguments (and produces a list)
                - '+' consumes one or more arguments (and produces a list)
            Note that the difference between the default and nargs=1 is that
            with the default, a single value will be produced, while with
            nargs=1, a list containing a single value will be produced.

        - default -- The value to be produced if the option is not specified.

        - type -- A callable that accepts a single string argument, and
            returns the converted value.  The standard Python types str, int,
            float, and complex are useful examples of such callables.  If None,
            str is used.

        - choices -- A container of values that should be allowed. If not None,
            after a command-line argument has been converted to the appropriate
            type, an exception will be raised if it is not a member of this
            collection.

        - metavar -- The name to be used for the option's argument with the
            help string. If None, the 'dest' value will be used as the name.
    """

    def __init__(self,
                 dest: str,
                 nargs: typing.Union[None, int, str] = None,
                 default: typing.Any = None,
                 type: typing.Callable = str,
                 # choices: typing.Tuple[str] = None,
                 metavar: str = None):
        self.dest = dest
        self.nargs = nargs
        self.default = default
        self.type = type
        # self.choices = choices
        self.metavar = metavar

    def _get_kwargs(self):
        names = [
            'dest',
            'nargs',
            'default',
            'type',
            # 'choices',
            'metavar',
        ]
        return [(name, getattr(self, name)) for name in names]

    def __call__(self, parser, namespace: Namespace, values: typing.List[typing.Any]):
        raise NotImplementedError('.__call__() not defined')

    @property
    def min_args(self):
        """
        Get the minimum amount of arguments this action can take
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
    def max_args(self):
        """
        Get the maximum amount of arguments this action can take
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

    def __call__(self, parser, namespace: Namespace, values: typing.List[typing.Any]):
        setattr(namespace, self.dest, values)


class JoinAction(Action):
    """
    This action takes strings and joins them with spaces.
    """

    def __init__(self,
                 dest,
                 nargs=None,
                 default=None,
                 type=str,
                 # choices=None,
                 metavar=None):
        if type is not str:
            raise ValueError("type has to be str")
        super().__init__(dest,
                         nargs=nargs,
                         default=default,
                         type=type,
                         # choices=choices,
                         metavar=metavar)

    def __call__(self,
                 parser,
                 namespace: Namespace,
                 values: typing.List[str]):
        setattr(namespace, self.dest, " ".join(values))
