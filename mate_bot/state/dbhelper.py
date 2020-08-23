#!/usr/bin/env python3

"""
Database management helper
"""

import typing
import pymysql as _pymysql

from config import config as _config


def execute(cmd: str) -> typing.Tuple[int, typing.Union[tuple, typing.List[typing.Dict[str, typing.Any]]]]:
    """
    Connect to the database, execute a single query and return results

    :param cmd: complete SQL query string without any placeholders
    :type cmd: str
    :return: tuple of number of the resulting query and the fetched data
    :rtype: tuple
    """

    connection = _pymysql.connect(**_config["database"], cursorclass=_pymysql.cursors.DictCursor)
    if connection.open:
        try:
            with connection.cursor() as cursor:
                state = cursor.execute(cmd)
                connection.commit()
                result = cursor.fetchall()
        finally:
            connection.close()
    else:
        raise _pymysql.err.OperationalError("No open connection")
    return state, result
