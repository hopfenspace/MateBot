"""
MateBot registry of available executors

Every dictionary in this module stores the executors
for exactly one handler type. The key type for every
dictionary is a string. However, some dictionaries
want to use this keys as patterns/filters for the
handlers, too. The following list covers the four
different module's attributes and describes their use:

  - ``commands`` is the only pool of executors that uses
    the name of the command as key and does therefore not
    filter incoming commands in the handler class. The
    class ``CommandHandler`` is used for all values, while
    the type of all values is ``BaseCommand`` or a subclass.
  - ``callback_queries`` is a pool of executors that handle
    incoming callback queries. Those are created when a user
    clicks/taps on an inline keyboard, for example. The key
    of this dictionary is used as a pattern to filter incoming
    updates. The handler class is ``CallbackQueryHandler``.
    The value type is ``BaseCallbackQuery`` or a subclass.
  - ``inline_queries`` is a pool of executors that handle
    incoming inline queries. Those are created when the user
    performs an inline search. Take a look into Telegram's
    `documentation <https://core.telegram.org/bots/inline>`_
    for further information. The key of this dictionary is used
    as pattern to filter incoming updates, too. And the handler
    class is ``InlineQueryHandler``, while the type of all
    stored values is ``BaseInlineQuery`` or a subclass.
  - ``inline_results`` is a pool of executors that handle
    incoming inline result updates. When a user performs an
    inline search using the previously mentioned queries,
    Telegram will send an update about the chosen inline result.
    (This must be enabled in the bot settings to work properly.)
    The key of this dictionary is used as pattern to filter
    incoming updates, too. The handler class is
    :class:`FilteredChosenInlineResultHandler`. The type of
    all stored values is ``BaseInlineResult`` or a subclass.
"""


commands: dict = {}
callback_queries: dict = {}
inline_queries: dict = {}
inline_results: dict = {}
