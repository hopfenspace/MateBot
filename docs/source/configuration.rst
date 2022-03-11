.. _configuration:

=============
Configuration
=============

.. toctree::

The configuration of the MateBot core API is stored in a JSON file
called ``config.json``. It should be placed in the top-level directory
of the Python source code files. A sample configuration may
look like the following snippet (see below for a brief explanation
of the different options the config file provides):

.. literalinclude:: _static/config.sample.json
    :language: json

.. only:: builder_html

    Download the sample config file
    :download:`config.sample.json <_static/config.sample.json>`.

General settings
----------------

The general section of the config provides the following options:

* ``min_refund_approves`` refers to the total number of votes required to
  approve an open refund request and therefore accept it automatically
* ``min_refund_disapproves`` refers to the total number of votes required
  to disapprove an open refund request and therefore reject it automatically
* ``min_membership_approves`` refers to the total number of votes required
  to approve an open membership request and therefore accept it automatically
* ``min_membership_disapproves`` refers to the total number of votes required
  to disapprove an open membership request and therefore reject it automatically
* ``max_parallel_debtors`` refers to the maximum number of debtors a single
  voucher user can have in parallel (this feature is currently not implemented)
* ``max_simultaneous_consumption`` refers to the maximum number of
  consumables a single user may consume in a single transaction
* ``max_transaction_amount`` refers to the highest amount a user may
  transfer to another user in a single transaction

Server settings
---------------

The server section of the config provides the following options:

* ``host`` defines the host the server should bind to
* ``port`` defines the port the server should bind to
* ``password_iterations`` defines the number of password iterations for
  the key derivation function (basically multiple uses of the hash function)

.. note::

    The ``host`` and ``port`` settings may be overwritten either by command-line
    arguments or via uvicorn config files that are used to directly run
    uvicorn with the ASGI application instead of calling the Python module.

.. warning::

    Once initialized, you can't change the ``password_iterations`` settings, since
    it would prevent applications to login with their previously hashed password!

Consumable definitions
----------------------

The consumable section of the config is a list of
entries of the following format:

* ``id`` refers to the internal ID of the consumable, which must be a
  unique number, starting from ``1`` and increasing (this is currently
  used since auto-enumerating of the consumable schemas doesn't work yet)
* ``name`` refers to the name of the consumable, which ideally is just a
  single word or abbreviation to uniquely identify the consumable for users,
  since MateBot clients are encouraged to use this name as command shortcut
* ``description`` may be a multi-word description of the consumable, which
  may be shown to users when they show details about a specific consumable
* ``price`` is the amount of money a user has to pay to the community
  user when consuming a single item of this consumable type

Database settings
-----------------

The database section of the config provides the following options:

* ``connection`` must be the correct and full DB URL (connection string)
  to the MateBot database; see the explanation about database URLs
  `in the SQLAlchemy docs <https://docs.sqlalchemy.org/en/14/core/engines.html#database-urls>`_
  for more information or head directly to the specification of them in
  `RFC 1738 <https://rfc.net/rfc1738.html>`_ (examples of such connection
  strings: ``sqlite:///matebot.db``, ``mysql://user:password@localhost/matebot``)
* ``debug_sql`` is a boolean that allows easier debugging of
  SQL operations, since all operations emitted to the database
  are also printed to standard output (note that this output
  may be pretty verbose in some circumstances)

.. note::

    Here's a list of some suggested external drivers for various databases:

      * `sqlite3 <https://docs.python.org/3/library/sqlite3.html>`_
        comes pre-installed with the Python standard library
      * `pymysql <https://pypi.org/project/PyMySQL>`_ is a pure-Python MySQL driver
      * `mysqlclient <https://pypi.org/project/mysqlclient>`_
        is a MySQL driver using the MySQL C libraries
      * `psycopg2 <https://pypi.org/project/psycopg2>`_ is the most popular
        database driver for PostgreSQL

    Asynchronous SQL database drivers are not supported.

.. warning::

    Do not run unittests with your production database, since they will
    manipulate data and/or destroy tables. Head to :ref:`testing` for details.

Logging settings
----------------

The whole content of the logging section of the configuration file is
directly passed to Python's ``logging`` module, specifically to the
`dictConfig <https://docs.python.org/3/library/logging.config.html#logging.config.dictConfig>`_
function. Refer to the Python documentation for more information.
