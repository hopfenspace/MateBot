#!/usr/bin/env python3

import argparse
from argparse import Action
import typing
from typing import Iterable, Optional


_ArgumentGroup = typing.NewType("_ArgumentGroup", object)


class ChatHelpFormatter(argparse.HelpFormatter):
    """
    A HelpFormatter whose output looks good in telegram chats.
    """

    def _format_usage(
            self,
            usage: Optional[str],
            actions: Iterable[Action],
            groups: Iterable[_ArgumentGroup],
            prefix: Optional[str]
    ) -> str:
        """
        foo
        """

        if prefix is None:
            prefix = _("Usage: `")

        # Generate the usage
        usage = super()._format_usage(None, actions, groups, prefix)

        # Put backtick between the actual string and the tailing two newlines
        usage = usage[:-2] + "`" + "\n\n"

        return usage
