#!/usr/bin/env python3

import argparse
import typing


class JoinAction(argparse.Action):
    """
    This action takes strings and joins them with spaces.
    """

    def __init__(self,
                 option_strings,
                 dest,
                 nargs=None,
                 const=None,
                 default=None,
                 type=str,
                 choices=None,
                 required=False,
                 help=None,
                 metavar=None):
        if type is not str:
            raise ValueError("type has to be str")
        super().__init__(option_strings, dest, nargs, const, default, type, choices, required, help, metavar)
       
    def __call__(self,
                 parser: argparse.ArgumentParser,
                 namespace: argparse.Namespace,
                 values: typing.List[str],
                 option_string: str = None):
        setattr(namespace, self.dest, " ".join(values))
