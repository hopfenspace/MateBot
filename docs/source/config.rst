=====================
Initial Configuration
=====================

.. toctree::


To deploy your own instance of the MateBot, you have to gather a BotToken from the `@Botfather` first. To do so follow the instructions on `the official telegram website <https://core.telegram.org/bots#6-botfather/>`_.

.. code-block:: json

    {
        "bot-token": "your telegram bot token here",

        "chat-id": 0,
        "max-amount": 50,
        "pay-min-users": 2,

        "members": [
                0
        ],

        "database": {
                "host": "localhost",
                "port": 3306,
                "db": "database_name",
                "user": "username",
                "password": "password",
                "charset": "utf8mb4"
        }
    }


The parameter `chat-id` specifies the chat, the bot should accept incoming commands from.

The parameter `max-amount` specifies the maximum amount a user can send or pay measured in Euro.

The parameter `pay-min-user` specifies the overall delta of members which has to approve. E.g. the pay / communism is approved if 1 member disapprove, but 3 approve.

The parameter `members` specifies the members which have the possibility to approve or disapprove pays / communisms. The members are represented as chat-ids.
**This parameter is outdated and will be removed in a future version.** See the `permission` flag in the `users` table in the configuration for the :ref:`database`.

The parameter `database` specifies the connection details to your database. Only MySQL / MariaDB are currently supported. The user has to have full permission on the database to create the needed tables.
To do so execute the following statements (don't forget to change the password!):

.. code-block:: sql
    
    CREATE DATABASE matedb;
    CREATE USER matebot_user IDENTIFIED BY 'mate2moneyPW=great';
    GRANT ALL PRIVILEGES ON matedb.* TO matebot_user;
    FLUSH PRIVILEGES;

For more information regarding the database, see :ref:`database`.
