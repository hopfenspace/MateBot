.. _config:

=====================
MateBot configuration
=====================

.. toctree::

The configuration of the MateBot is stored in a JSON file called
``config.json``. It should be placed in the top-level directory
of the Python source code files. A sample configuration may
look like the following snippet (see below for a brief explanation
of the different options the config file provides):

.. literalinclude:: ../../config.json
    :language: json

General settings
----------------

The parameter ``max-amount`` specifies the highest amount
a user can send to someone else, get back by a community payment
or collect in a communism. It is measured in Cent.

The option ``max-consume`` sets the upper limit of consumed
goods in one command. This ensures that no one executes
something like ``/drink 10000`` which in turn avoids trouble.

The flag ``db-localtime`` states whether the database returns already
localized timestamps. This is used in formatting transactions.

Bot settings
------------

The config parameter ``token`` holds your Telegram bot token.
It is needed to identify and authenticate the service against
the Telegram API. See the official Telegram website about the
`Telegram bots <https://core.telegram.org/bots>`_ and write
to `@BotFather <https://t.me/botfather>`_ to gain your token.

In order to use all features of the bot (including the
inline search features), you need to perform the following
two commands in the chat with ``@BotFather``:

.. code-block::

    /setinline
    /setinlinefeedback

.. note::

    You need to set the quota for the inline feedback to 100%,
    otherwise the inline search features will not work properly.

Chat settings
-------------

The first parameter ``internal`` specifies the ID of the chat
the bot should treat as privileged or "internal". Members of
this chat are expected to be members of the core community.
Some commands are restricted to internal members only. To become
such an internal member, write any command to the internal group.

The other four options are lists of those chat IDs. They accept
zero or more chat IDs which have the following meaning:

* All chats mentioned in the ``transactions`` list will receive
  transaction logs whenever someone performs an action that changes
  the amount of money of any user (including the community user).
* All chats mentioned in the ``notification`` list will receive
  notifications when the bot's error handler caught an unhandled
  exception. This is seen as the very basic level of debugging.
* All chats mentioned in the ``stacktrace`` list will receive
  the full Python stacktrace in case an unhandled exception reaches
  the bot's error handler. This works similar to the above list
  but includes a lot more detail to find and fix any errors.
* All chats mentioned in the ``debugging`` list will receive
  the same messages as the ``stacktrace`` group does. However,
  an additional message containing the ``Update`` object that
  caused the error is also sent to each of the mentioned chats.

.. note::

    You may not specify too many different debugging chats. This
    might cause the bot to hit certain rate limits, which in
    turn causes other problems. Create a group of developers
    and add the bot to this group instead to avoid those limits.

.. _config_community:

Community settings
------------------

The settings ``payment-consent`` and ``payment-denial``
specify the overall delta of members who have approved
or disapproved a payment operation. By default, a payment
is accepted if two or more of the permitted members vote for
it (approve it). On the other side, a payment is automatically
denied if, by default, two or more members vote against it
(disapprove it). Note that the delta of all votes is considered.
For example, a payment is accepted when one member disapproved
but three members approved the operation.

Remember that only members are allowed to vote for and against
a payment. A user is considered a member if it's not marked
as external and has the ``permission`` flag set in its record.

The option ``multiple-externals`` specifies whether a user is
allowed to vouch for more than one external user. External users
must have an internal user (which is not necessarily a member
with permissions to vote) that vouches for that external one.
If no one vouches for an external, it is not allowed to perform
certain operations like sending money or consuming goods.

Database settings
-----------------

The database settings provide necessary details about the
connection to the MySQL / MariaDB server. Other database
servers are currently not supported. A user with full
permission for the particular database is needed. Therefore,
you could follow the instructions below to create a new
user that is used by the bot to interact with the database.
**Do not forget to change the password!**

.. code-block:: sql

    CREATE DATABASE matedb;
    CREATE USER matebot_user IDENTIFIED BY 'password';
    GRANT ALL PRIVILEGES ON matedb.* TO matebot_user;
    FLUSH PRIVILEGES;

If you want to be able to perform unittests as well, you
should create a second table and configure it in the
``testing`` section (see below).

For more information regarding the database, see :ref:`database`.

Testing Settings
----------------

This section will be used to update / overwrite the main database
settings. This allows the use of a second database in tests
without influencing the actual data in the first one.

Consumable Definitions
----------------------

Here you can define your own "consumables". Every kind
of food and drink should be treated as such. These are
dynamically created commands which let you pay a
static price corresponding to a consumable good.

For example, in the default configuration, you can perform
a ``/drink`` command when you take a drink out of the fridge.
This will make you pay the static amount to the community user.
In our defaults, this are 100 units of money, where the unit
is Cent by default. You can create your own commands for
consumption using the following parameters:

  - ``name`` refers to the command's name.
  - ``description`` is a custom description shown by the ``/help``
    command. It will be created dynamically, if an empty string is given.
  - ``price`` refers to the static amount of money to pay.
  - ``messages`` is a list of strings. One of those messages will be chosen
    randomly as a reply to the user when successfully paying the money.
  - ``symbol`` is a UTF-8 symbol to append to the reply message.
    If more than one of the goods is consumed (by giving an integer parameter
    to the command), this symbol will be send so many times.
