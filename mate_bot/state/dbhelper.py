"""
MateBot database management helper library
"""

import typing

try:
    import MySQLdb as pymysql
    import MySQLdb.connections
    import MySQLdb.cursors

    pymysql.connections = MySQLdb.connections
    pymysql.cursors = MySQLdb.cursors

except ImportError:
    import pymysql
    pymysql.install_as_MySQLdb()
    MySQLdb = None

from mate_bot.config import config as _config


QUERY_RESULT_TYPE = typing.List[typing.Dict[str, typing.Any]]
EXECUTE_TYPE = typing.Tuple[int, QUERY_RESULT_TYPE]
EXECUTE_NO_COMMIT_TYPE = typing.Tuple[int, QUERY_RESULT_TYPE, pymysql.connections.Connection]

DATABASE_SCHEMA = {
    "users": (
        "id",
        "tid",
        "username",
        "name",
        "balance",
        "permission",
        "active",
        "created",
        "accessed"
    ),
    "transactions": (
        "id",
        "sender",
        "receiver",
        "amount",
        "reason",
        "registered"
    ),
    "collectives": (
        "id",
        "active",
        "amount",
        "externals",
        "description",
        "communistic",
        "creator",
        "created"
    ),
    "collectives_users": (
        "id",
        "collectives_id",
        "users_id",
        "vote"
    ),
    "collective_messages": (
        "id",
        "collectives_id",
        "chat_id",
        "msg_id"
    ),
    "externals": (
        "id",
        "internal",
        "external",
        "changed"
    )
}


def execute_no_commit(
        query: str,
        arguments: typing.Union[tuple, list, dict, None] = None,
        connection: typing.Optional[pymysql.connections.Connection] = None
) -> EXECUTE_NO_COMMIT_TYPE:
    """
    Connect to the database, execute a single query and return results and the database connection

    Use this function in case you need more than one query to fulfill your needs.
    All your queries will be cached on the server side as long as you don't call
    the .commit() method on the returned Connection object to save the changes
    you introduced during your previous queries. Important: When the program exits
    or the connection is closed without calling .commit(), the introduced changes
    are lost! So, be careful and enclose this call in a try-finally-block:

        try:
            rows, result, connection = execute_no_commit(...)
            ...
            connection.commit()
        finally:
            if connection:
                connection.close()

    :param query: SQL query string that might contain placeholders
    :type query: str
    :param arguments: optional collection of arguments that should be passed into the query
    :type arguments: tuple, list, dict or None
    :param connection: optional connection to the database (it will be opened implicitly if None)
    :type connection: typing.Optional[pymysql.connections.Connection]
    :return: number of affected rows, the fetched data and the open database connection
    :rtype: tuple
    :raises TypeError: when the connection is neither None nor a valid Connection
    :raises pymysql.err.OperationalError: when the database connection is closed
    """

    if connection is None:
        connection = pymysql.connect(**_config["database"], cursorclass=pymysql.cursors.DictCursor)
    elif not isinstance(connection, pymysql.connections.Connection):
        raise TypeError("Invalid connection type")

    if connection.open:
        with connection.cursor() as cursor:
            rows = cursor.execute(query, arguments)
            result = list(cursor.fetchall())
    else:
        raise pymysql.err.OperationalError("No open connection")
    return rows, result, connection


def execute(
        query: str,
        arguments: typing.Union[tuple, list, dict, None] = None
) -> EXECUTE_TYPE:
    """
    Connect to the database, execute and commit a single query and return results

    :param query: SQL query string that might contain placeholders
    :type query: str
    :param arguments: optional collection of arguments that should be passed into the query
    :type arguments: tuple, list, dict or None
    :return: number of affected rows and the fetched data
    :rtype: tuple
    """

    connection = None
    try:
        rows, result, connection = execute_no_commit(query, arguments)
        connection.commit()
    finally:
        if connection:
            connection.close()
    return rows, result
