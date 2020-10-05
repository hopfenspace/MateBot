.. _installation_setup:

======================
Installation and setup
======================

.. toctree::

Environment setup
-----------------

Prerequisites
~~~~~~~~~~~~~

This bot was developed under and tested with Debian GNU/Linux. It might
work with other operating systems of the Linux family as well as other
UNIX systems, as long as those support the required libraries. We do not
support Windows and Mac OS and have no plans to do so.

We encourage you to use another user to run the bot for security purposes,
e.g. ``matebot`` or ``matebot_user`` (just anything but ``root`` of course).
Choose a name and stick to it during this setup.

You need to have at least `Python 3.7 <https://www.python.org/downloads>`_
with ``pip`` and ``venv`` installed on your system. You will also need a
MariaDB or MySQL server (other database backends are currently not supported).

On Debian GNU/Linux and its derivatives, the following snippet should do the
steps for you (you need to be ``root`` or prefix the commands with ``sudo``):

.. code-block::

    apt update
    apt upgrade -y
    apt install mariadb-server python3 python3-pip python3-venv git -y
    mysql_secure_installation

Code setup
~~~~~~~~~~

Clone our repository to your server:

.. code-block::

    git clone https://github.com/CrsiX/matebot
    cd matebot

Create and enable a virtual environment for the Python packages:

.. code-block::

    python3 -m venv venv
    source venv/bin/activate

Install the minimally required Python packages:

.. code-block::

    pip3 install -r requirements.txt

.. note::

    You may have `mysqlclient <https://pypi.org/project/mysqlclient/>`_
    installed on your machine. In case it's available, we prefer it over
    `pymysql <https://pypi.org/project/PyMySQL/>`_, which is installed
    because it's listed in the ``requirements.txt`` file. However, it
    requires the installation of OS-specific libraries which the pure-Python
    implementation does not. Therefore, there's the requirement for the
    pure-Python library, while the other one could be used by doing:

    .. code-block::

        apt install default-libmysqlclient-dev
        pip3 install mysqlclient

Telegram Bot Setup
------------------

To deploy your own instance of the MateBot, you have to create a Telegram bot.
Talk to `@BotFather <https://t.me/botfather>`_ to create your own bot
and gather a bot token. To do so follow the instructions on the official
`Telegram website <https://core.telegram.org/bots#6-botfather>`_.

The token may look something like this:
``1153242342:AA3ofnI2ABvleFEmPq9naIfeY9Y2afeof2v``.
Store it in the config option ``bot:token`` as shown below.

MateBot Configuration
---------------------

The configuration of the MateBot is stored in a JSON file called
``config.json``. It should be placed in the top-level directory
of the Python source code files. A sample configuration may
look like the following snippet (see below for a brief explanation
of the different options the config file provides):

.. literalinclude:: ../../config.json
    :language: json

General settings
~~~~~~~~~~~~~~~~

The parameter ``max-amount`` specifies the highest amount
a user can send to someone else, get back by a community payment
or collect in a communism. It is measured in Cent.

The option ``max-consume`` sets the upper limit of consumed
goods in one command. This ensures that no one executes
something like ``/drink 10000`` which in turn avoids trouble.

The flag ``db-localtime`` states whether the database returns already
localized timestamps. This is used in formatting transactions.

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
~~~~~~~~~~~~~~~~

This section will be used to update / overwrite the main database
settings. This allows the use of a second database in tests
without influencing the actual data in the first one.

Development Settings
~~~~~~~~~~~~~~~~~~~~

In these lists a developer or admin can register chat ids
to be notified of internal errors.

When an unhandled error occurs in the execution of a command.
The bot will go through these lists and send a message to each chat id
contained in them. The lists correspond to the level of detail the message
contains:

``notification``
""""""""""""""""
receives just the error message

``description``
"""""""""""""""
receives the whole traceback

``debugging``
"""""""""""""
receives the traceback as well as the whole update object
which triggered the error as json

Consumables Definitions
~~~~~~~~~~~~~~~~~~~~~~~

Here you can define your own consumables.

These are dynamically created commands which pay a static price corresponding
to a consumable good. For example when someone takes a drink from the fridge
you pay 1€ by sending a ``/drink``. Commands like this can be defined here.

Each consumable needs these following parameters:

``name``
""""""""
The commands name.

``description``
"""""""""""""""
A custom description shown by the ``/help`` command.
It will be created dynamically, if an empty string is given.

``price``
"""""""""
The amount to pay in cents.

``messages``
""""""""""""
A list of messages. One will be selected randomly an send as a reply.

``symbol``
""""""""""
A utf8 symbol to append to the reply message. If more than one
is consumed (by giving an integer parameter to the command), this
symbol will be send so many times.
