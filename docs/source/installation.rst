.. _installation:

============
Installation
============

.. toctree::

System requirements
-------------------

Around 80 MiB of RAM and a single CPU core are totally fine,
but the more the better. However, note that a SQLite database
and the Python GIL may be a bottleneck. Consider a full database
server deployment and adapt the uvicorn configuration to use
multiple worker processes to improve response times and speed.

This project was developed under and tested with Debian GNU/Linux. It might
work with other operating systems of the Linux family as well as other
UNIX systems, as long as those support the required libraries. We do not
"officially" support Windows and Mac OS and have no plans to do so.

Prerequisites
-------------

We encourage you to use another user to run the API for security purposes,
e.g. ``matebot`` or ``matebot_user`` (just anything but ``root`` of course).
Choose a name and stick to it during this setup. A simple tool to
create a new user on a Debian-like machine is ``adduser``.

You need to have at least `Python 3.7 <https://www.python.org/downloads>`_
with ``pip`` and ``venv`` installed on your system. Those can be installed
using ``apt install python3-pip python3-venv`` on Debian-like systems and
using ``dnf install python3-pip`` on Fedora-like systems.

Even though the API works with a single SQLite database, it's highly
recommended to utilize a deployment-grade database server. We currently
support MySQL / MariaDB, but all SQL database backends with drivers
for ``sqlalchemy`` should be fine, too.

Additionally, you either need ``git`` or download the release files as archive.

On Debian GNU/Linux and its derivatives, the following snippet should do the
steps for you (you need to be ``root`` or prefix the commands with ``sudo``):

.. code-block::

    apt-get update
    apt-get upgrade -y
    apt-get install mariadb-server python3 python3-pip python3-venv git -y
    mysql_secure_installation

.. _installation_database:

Database configuration
----------------------

Log into your database server. It requires an account that can create
users, databases and set privileges. You can choose any user and database name
you want. **Do not forget to change the password of the new database user!**
For a MySQL / MariaDB server, the following snippet should do the trick:

.. code-block:: sql

    CREATE USER 'matebot_core'@localhost IDENTIFIED BY 'password';
    CREATE DATABASE matebot_core;
    GRANT ALL PRIVILEGES ON matebot_core.* TO 'matebot_core'@localhost;
    FLUSH PRIVILEGES;

In case you want to be able to perform unittests with your database,
you should also create a second database and call it something like
``matebot_core_test`` or so. Read :ref:`testing` for more information.

Installation instructions
-------------------------

The following steps should be executed as your target user
(e.g. ``matebot_core`` or ``matebot_user``). Login or enable
it with ``su - matebot_core`` or ``sudo -su matebot_user``.

1. Clone our repository to your server:

    .. code-block::

        git clone https://github.com/hopfenspace/MateBot
        cd MateBot

2. Create and enable a virtual environment for the Python packages:

    .. code-block::

        python3 -m venv venv
        source venv/bin/activate

3. Install the minimally required Python packages:

    .. code-block::

        pip3 install -r requirements.txt

    .. note::

        We don't enforce any database drivers as dependencies in the
        ``requirements.txt`` file. The database driver must be installed extra.
        We "officially" support SQLite and MySQL / MariaDB, but everything
        supported by `SQLAlchemy <https://docs.sqlalchemy.org/en/14/dialects>`_
        may work. See :ref:`configuration` for more information.

4.  Initialize the MateBot core data once using ``init``. You will be asked
    to enter the database connection string (including the SQL driver for
    SQLAlchemy) and a name for the community user (the one user account
    owning consumables and refunding payments for everybody):

    .. code-block::

        python3 -m matebot_core init --help
        python3 -m matebot_core init

5.  Edit the newly created configuration file ``config.json``.
    Refer to :ref:`configuration` for more information about
    available options and their meaning. To get started quickly,
    it's enough to just configure the server settings now.

6.  Create new application accounts to authenticate against the API.
    The password may either be given via the ``--password``
    option or interactively via standard input:

    .. code-block::

        python3 -m matebot_core add-app --help
        python3 -m matebot_core add-app --app <APPLICATION NAME>

Execution
---------

You can now easily start the MateBot core API using the ``run`` command:

.. code-block::

    python3 -m matebot_core run --help
    python3 -m matebot_core run

It's also possible to run ``uvicorn`` directly to execute the
project's ASGI application (in this case, the server settings
of the ``config.json`` file are ignored!):

.. code-block::

    uvicorn matebot_core.api:api

Another way to run the application is by using ``nginx`` as a reverse
proxy. This is the recommended setup when the API is reachable globally.
See `the uvicorn docs <https://www.uvicorn.org/deployment>`_ for more
information about deployments and various sample configuration.

Upgrading
---------

This project uses `alembic <https://alembic.sqlalchemy.org>`_ to handle
database migrations. Ideally, the upgrade procedure would contain those steps:

1. Read the release notes, because they may contain additional information.
2. Shutdown the web server.
3. Make a backup of the database.
4. Pull the new version of the project
   (e.g. ``git fetch origin && git checkout <new version tag>``).
5. Run ``venv/bin/alembic upgrade head``.
6. Start the web server again.

Systemd service
---------------

On systemd-enabled systems, it's recommended to add a systemd service
to start the MateBot core API automatically. To do so, call the module
with the ``systemd`` command, edit the service file, add a symlink to it,
reload the systemd daemon and finally enable the new service.
All steps as an example below:

.. code-block::

    python3 -m matebot_core systemd
    sudo ln -vrs matebot_core.service /lib/systemd/system/matebot_core.service
    sudo systemctl daemon-reload
    sudo systemctl enable matebot_core
    sudo systemctl start matebot_core
