=====================
Initial Configuration
=====================

.. toctree::

Telegram Bot Setup
------------------

To deploy your own instance of the MateBot, you have to gather a bot
token from `@BotFather` first. To do so follow the instructions on
`the official telegram website <https://core.telegram.org/bots#6-botfather/>`_.

The token may look something like this:
``1153242342:AA3ofnI2ABvleFEmPq9naIfeY9Y2afeof2v``.
Store it in the config option ``token`` as shown below.

MateBot Configuration
---------------------

The configuration of the MateBot is stored in a JSON file called
``config.json``. It should be placed in the top-level directory
of the Python source code files. A sample configuration may
look like the following snippet (see below for a brief explanation
of the different options the config file provides):

.. code-block:: json

    {
        "general": {
            "max-amount": 10000,
            "max-consume": 10
        },
        "bot": {
            "token": "<Telegram bot token here>",
            "chat": 0
        },
        "community": {
            "payment-consent": 2,
            "payment-denial": 2,
            "multiple-externals": true
        },
        "database": {
            "host": "localhost",
            "port": 3306,
            "db": "database_name",
            "user": "username",
            "password": "password",
            "charset": "utf8mb4"
        }
    }

General settings
~~~~~~~~~~~~~~~~

The parameter ``max-amount`` specifies the heighest amount
a user can send to someone else, get back by a community payment
or collect in a communism. It is measured in Cent.

The option ``max-consume`` sets the upper limit of consumed
goods in one command. This ensures that no one executes
something like ``/drink 10000`` which in turn avoids trouble.

Bot settings
~~~~~~~~~~~~

The option ``token`` holds your Telegram bot token
as shown in the previous section.

The parameter ``chat`` specifies the ID of the chat
the bot should accept incoming commands from. This is
a security measure, as all money transactions via the bot
are publicly visible by all members of the group (because
it's only useful if the chat ID refers to a Telegram group).

Community settings
~~~~~~~~~~~~~~~~~~

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
~~~~~~~~~~~~~~~~~

The database settings provide necessary details about the
connection to the MySQL / MariaDB server. Other database
servers are currently not supported. A user with full
permission for the particular database is needed. Therefore,
you could follow the instructions below to create a new
user that is used by the bot to interact with the database.
*Do not forget to change the password!*

.. code-block:: sql

    CREATE DATABASE matedb;
    CREATE USER matebot_user IDENTIFIED BY 'password';
    GRANT ALL PRIVILEGES ON matedb.* TO matebot_user;
    FLUSH PRIVILEGES;

For more information regarding the database, see :ref:`database`.
