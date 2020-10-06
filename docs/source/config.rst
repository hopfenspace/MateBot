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

The option ``token`` holds your Telegram bot token
as shown in the previous section.

The parameter ``chat`` specifies the ID of the chat
the bot should accept incoming commands from. This is
a security measure, as all money transactions via the bot
are publicly visible by all members of the group (because
it's only useful if the chat ID refers to a Telegram group).

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

Development Settings
--------------------

The following set of lists stores Telegram chat IDs. The bot
will send messages to those chats in case an internal error occurs.
The lists define the level of detail for the sent message:

  - ``notification``
    receives the error message of error but not the error type.
  - ``description``
    receives the whole traceback of the error.
  - ``debugging``
    receives the traceback similar to the previous list as well as
    the whole Update object associated with the error. This Update
    object will be indented and formatted using like JSON data.

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
