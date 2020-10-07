"""
MateBot registry of available executors
"""

from typing import Dict as _Dict

from mate_bot.commands.base import (
    BaseCommand as _BaseCommand,
    BaseCallbackQuery as _BaseCallbackQuery,
    BaseInlineQuery as _BaseInlineQuery,
    BaseInlineResult as _BaseInlineResult
)


commands: _Dict[str, _BaseCommand] = {}
callback_queries: _Dict[str, _BaseCallbackQuery] = {}
inline_queries: _Dict[str, _BaseInlineQuery] = {}
inline_results: _Dict[str, _BaseInlineResult] = {}
