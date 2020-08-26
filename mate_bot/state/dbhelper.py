#!/usr/bin/env python3

"""
Database management helper
"""

import typing
import pymysql as _pymysql

from config import config as _config


def execute(
        query: str,
        arguments: typing.Union[tuple, list, dict, None] = None
) -> typing.Tuple[int, typing.Union[tuple, typing.List[typing.Dict[str, typing.Any]]]]:
    """
    Connect to the database, execute a single query and return results

    :param query: SQL query string that might contain placeholders
    :type query: str
    :param arguments: optional collection of arguments that should be passed into the query
    :type arguments: tuple, list, dict or None
    :return: tuple of number of affected rows and the fetched data
    :rtype: tuple
    """

    connection = _pymysql.connect(**_config["database"], cursorclass=_pymysql.cursors.DictCursor)
    if connection.open:
        try:
            with connection.cursor() as cursor:
                state = cursor.execute(query, arguments)
                connection.commit()
                result = cursor.fetchall()
        finally:
            connection.close()
    else:
        raise _pymysql.err.OperationalError("No open connection")
    return state, result
