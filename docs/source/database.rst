.. _database:

========
Database
========

.. toctree::

********************
Database Information
********************

Overview
========


Table layouts
=============

Table ``users``
^^^^^^^^^^^^^^^

+------------+--------------+----------+---------+-----------------------+-----------------------------+
| Field      | Type         | Null     | Key     | Default               | Extra                       |
+============+==============+==========+=========+=======================+=============================+
| id         | int(11)      | ``NO``   | ``PRI`` | ``NULL``              | auto_increment              |
+------------+--------------+----------+---------+-----------------------+-----------------------------+
| tid        | bigint(20)   | ``YES``  | ``UNI`` | ``NULL``              |                             |
+------------+--------------+----------+---------+-----------------------+-----------------------------+
| username   | varchar(255) | ``YES``  |         | ``NULL``              |                             |
+------------+--------------+----------+---------+-----------------------+-----------------------------+
| name       | varchar(255) | ``NO``   |         | ``NULL``              |                             |
+------------+--------------+----------+---------+-----------------------+-----------------------------+
| balance    | mediumint(9) | ``NO``   |         | ``0``                 |                             |
+------------+--------------+----------+---------+-----------------------+-----------------------------+
| permission | tinyint(1)   | ``NO``   |         | ``0``                 |                             |
+------------+--------------+----------+---------+-----------------------+-----------------------------+
| active     | tinyint(1)   | ``NO``   |         | ``1``                 |                             |
+------------+--------------+----------+---------+-----------------------+-----------------------------+
| created    | timestamp    | ``NO``   |         | ``CURRENT_TIMESTAMP`` |                             |
+------------+--------------+----------+---------+-----------------------+-----------------------------+
| accessed   | timestamp    | ``NO``   |         | ``CURRENT_TIMESTAMP`` | on update CURRENT_TIMESTAMP |
+------------+--------------+----------+---------+-----------------------+-----------------------------+

This table stores the whole user base and is the core of the database.

The `tid` value is the Telegram user ID. Virtual users must have set
``NULL`` here as they don't have a valid Telegram account. However, it's
expected that there is exactly one virtual user that has ``NULL`` here,
the special community user. This user will e.g. send successful payments
from its account to the other users. So, **make sure that there is
only one such user in this table** that has ``NULL`` here. Ignoring
this warning leads to unspecified behavior and may corrupt data.

The `username` is the Telegram username (starting with ``@``) if this was set.
However, the ``@`` will not be stored in the database. If no username is known for a
user, `username` will be ``NULL``. Virtual users should set the username to ``NULL``.

The `name` is the Telegram name consisting of the first and last name (as far as
the last name was set by the Telegram user). You can be sure that `name` will always
be a string and set to a valid value. This is also enforced for virtual users.

The `balance` is measured in Cent. Every new user must start with a balance of ``0``.

The `permission` flag should be ``false`` by default. Any user who was
white-listed will get the positive flag (``true``). This means that the
user is permitted to vote on payment operations.

The `active` flag determines if the user is permitted to perform any form of writing
operation, e.g. sending money to someone or asking for payments. This switch should
be used to handle inactive users. **Do not delete** users from the table. This would
also wipe out their transactions and corrupt the whole database's integrity.

The two timestamps `created` and `accessed` should be read-only values from the client.
The first determines the time when the user record was added to the table while the
second will be automatically updated on every update of a record and therefore stores
the time of the last edit of any value associated with a specific user.

Table ``transactions``
^^^^^^^^^^^^^^^^^^^^^^

+------------+--------------+----------+---------+-----------------------+----------------+
| Field      | Type         | Null     | Key     | Default               | Extra          |
+============+==============+==========+=========+=======================+================+
| id         | int(11)      | ``NO``   | ``PRI`` | ``NULL``              | auto_increment |
+------------+--------------+----------+---------+-----------------------+----------------+
| sender     | int(11)      | ``NO``   | ``MUL`` | ``NULL``              |                |
+------------+--------------+----------+---------+-----------------------+----------------+
| receiver   | int(11)      | ``NO``   | ``MUL`` | ``NULL``              |                |
+------------+--------------+----------+---------+-----------------------+----------------+
| amount     | mediumint(9) | ``NO``   |         | ``NULL``              |                |
+------------+--------------+----------+---------+-----------------------+----------------+
| reason     | varchar(255) | ``YES``  |         | ``NULL``              |                |
+------------+--------------+----------+---------+-----------------------+----------------+
| registered | timestamp    | ``NO``   |         | ``CURRENT_TIMESTAMP`` |                |
+------------+--------------+----------+---------+-----------------------+----------------+

This table stores all transactions that were ever committed. The data is
expected to be consistent if a user's current balance can be calculated
by adding all its transactions up (when starting with a balance of ``0``).

The `sender` and `receiver` are the two partners of a transaction.
They refer to users' IDs from the ``users`` table.

The `amount` is measured in Cent. It must be a positive integer value.

The `reason` is an optional description of (or reason for) the transaction.
But it is strongly encouraged to give a reason for a transaction.

The timestamp `registered` will be set to the current time when
the record was entered in the database to track the creation time.

Table ``collectives``
^^^^^^^^^^^^^^^^^^^^^

+-------------+--------------+----------+---------+-----------------------+----------------+
| Field       | Type         | Null     | Key     | Default               | Extra          |
+=============+==============+==========+=========+=======================+================+
| id          | int(11)      | ``NO``   | ``PRI`` | ``NULL``              | auto_increment |
+-------------+--------------+----------+---------+-----------------------+----------------+
| active      | tinyint(1)   | ``NO``   |         | ``1``                 |                |
+-------------+--------------+----------+---------+-----------------------+----------------+
| amount      | mediumint(9) | ``NO``   |         | ``NULL``              |                |
+-------------+--------------+----------+---------+-----------------------+----------------+
| externals   | smallint(6)  | ``YES``  |         | ``NULL``              |                |
+-------------+--------------+----------+---------+-----------------------+----------------+
| description | varchar(255) | ``YES``  |         | ``NULL``              |                |
+-------------+--------------+----------+---------+-----------------------+----------------+
| communistic | tinyint(1)   | ``NO``   |         | ``NULL``              |                |
+-------------+--------------+----------+---------+-----------------------+----------------+
| creator     | int(11)      | ``NO``   | ``MUL`` | ``NULL``              |                |
+-------------+--------------+----------+---------+-----------------------+----------------+
| created     | timestamp    | ``NO``   |         | ``CURRENT_TIMESTAMP`` |                |
+-------------+--------------+----------+---------+-----------------------+----------------+

This table stores all collective operations. More than two users can
participate in this operations. Also, see the table ``collectives_users``.

At first, a collective will always be active (``true``) by default. This means,
that it's currently worked on, e.g. users can vote or participate. After
committing the transaction(s) successfully, the `active` flag should be set
to ``false``. Users can not vote or participate on the collective anymore.

The `amount` is measured in Cent. It must not be zero. For payments, no
negative values are allowed. Communisms may use negative values. However,
this is not really useful in real-world scenarios. Therefore, it's highly
recommended to only use positive values as `amount` here.

The counter `externals` must be positive. It stores the number of external
persons without access to the bot that wanted to join a communism.
A default communism after initialization should store a ``0`` here.
For payments, this counter is silently ignored and should be ``NULL``.

The `description` is an optional text giving the reason for the collective.
It is handled similar to the `reason` of a transaction.

The `communistic` flag is a boolean value. If it's ``false``, then the
collective operation is a payment. Otherwise it is a communism (``true``).
Remember that the `externals` counter will be ignored on payments.

The field `creator` stores the user ID of the user who has started
the collective operation. One user may only have one active collective
operation at the same time if this is enforced by client software.

The timestamp `created` will be set automatically and stores the
timestamp when the collective was committed to the database.

Table ``collectives_users``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

+----------------+------------+----------+---------+-------------+----------------+
| Field          | Type       | Null     | Key     | Default     | Extra          |
+================+============+==========+=========+=============+================+
| id             | int(11)    | ``NO``   | ``PRI`` | ``NULL``    | auto_increment |
+----------------+------------+----------+---------+-------------+----------------+
| collectives_id | int(11)    | ``NO``   | ``MUL`` | ``NULL``    |                |
+----------------+------------+----------+---------+-------------+----------------+
| users_id       | int(11)    | ``NO``   | ``MUL`` | ``NULL``    |                |
+----------------+------------+----------+---------+-------------+----------------+
| vote           | tinyint(1) | ``NO``   |         | ``NULL``    |                |
+----------------+------------+----------+---------+-------------+----------------+

This table maps collectives and users together. A single record
in this table means that the user joined the collective operation.

The `collectives_id` is the key for the ID in the ``collectives`` table.
The `users_id` is the key for the user ID in the ``users`` table.

The value in the column `vote` should be ignored for communisms. The
code prefers to set the value to ``0`` in this case. However, the
value for `vote` defines whether a user approved (``1``) or
disapproved (``0``) a payment request. See :ref:`config_community`
about the configuration of the payment approval process.

Table ``collective_messages``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

+----------------+------------+----------+---------+-------------+----------------+
| Field          | Type       | Null     | Key     | Default     | Extra          |
+================+============+==========+=========+=============+================+
| id             | int(11)    | ``NO``   | ``PRI`` | ``NULL``    | auto_increment |
+----------------+------------+----------+---------+-------------+----------------+
| collectives_id | int(11)    | ``NO``   | ``MUL`` | ``NULL``    |                |
+----------------+------------+----------+---------+-------------+----------------+
| chat_id        | bigint(20) | ``NO``   |         | ``NULL``    |                |
+----------------+------------+----------+---------+-------------+----------------+
| msg_id         | int(11)    | ``NO``   |         | ``NULL``    |                |
+----------------+------------+----------+---------+-------------+----------------+

This table is used to keep track of messages sent by the bot. However,
it only stores collective managment messages (identified by the Chat ID
``chat_id`` in conjunction with the Message ID ``msg_id``) in this table.
Those messages handle exactly one collective operation by placing the
inline keyboard for the user below the message. Keeping track of them is
needed in order to update *all* messages when the data for one collective
has changed.

Table ``externals``
^^^^^^^^^^^^^^^^^^^

+----------+-----------+----------+---------+-----------------------+-----------------------------+
| Field    | Type      | Null     | Key     | Default               | Extra                       |
+==========+===========+==========+=========+=======================+=============================+
| id       | int(11)   | ``NO``   | ``PRI`` | ``NULL``              | auto_increment              |
+----------+-----------+----------+---------+-----------------------+-----------------------------+
| internal | int(11)   | ``YES``  | ``MUL`` | ``NULL``              |                             |
+----------+-----------+----------+---------+-----------------------+-----------------------------+
| external | int(11)   | ``NO``   | ``UNI`` | ``NULL``              |                             |
+----------+-----------+----------+---------+-----------------------+-----------------------------+
| changed  | timestamp | ``NO``   |         | ``CURRENT_TIMESTAMP`` | on update CURRENT_TIMESTAMP |
+----------+-----------+----------+---------+-----------------------+-----------------------------+

This table handles external users. Those have valid Telegram accounts
and are therefore no virtual users. To reduce the risk of abuse, there
must be an internal user that has to bail for the external user.

Users are automatically marked *external* when their user IDs appear
in the `external` column of this table. External users do not have vote
permissions on payments (ignoring their value in the ``users`` table).
Furthermore, external users do not have permissions to perform operations
as long as no internal user is attached to their record in this table.
