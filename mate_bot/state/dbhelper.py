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



class BackendHelper:
    """
    Helper class providing easy methods to read and write values in the database

    Instead of direct calls to the database using `execute`, this
    class provides a collection of static methods that make it easy
    to interact with the database as you don't need to know about the
    actual database query language. Any high level implementation
    may subclass this class in order to declare its area of usage.

    Use the functions ending with ``_manually`` in case you need more
    than one call to the functions defined here to fulfill your needs.
    All your queries will be cached on the server side as long as you
    don't call the ``.commit()`` method on the returned Connection object
    to save the changes you introduced during your previous queries.

    .. warning::

        Important! When the program exits or the connection is closed
        without calling ``.commit()``, the introduced changes are lost!
        So, be careful and enclose this call in a try-finally-block:

        .. code-block:: python3

                try:
                    rows, result, connection = execute_no_commit(...)
                    ...
                    connection.commit()
                finally:
                    if connection:
                        connection.close()
    """

    @staticmethod
    def _execute_no_commit(
            query: str,
            arguments: typing.Union[tuple, list, dict, None] = None,
            connection: typing.Optional[pymysql.connections.Connection] = None
    ) -> EXECUTE_NO_COMMIT_TYPE:
        """
        Connect to the database, execute a single query and return results and the connection

        .. note::

            Read the class documentation for :class:`BackendHelper` for more
            information about the functions ending with ``_manually``. Those
            functions use this :func:`_execute_no_commit` under the hood.


        :param query: SQL query string that might contain placeholders
        :type query: str
        :param arguments: optional collection of arguments that should be passed into the query
        :type arguments: tuple, list, dict or None
        :param connection: optional connection to the database (opened implicitly if None)
        :type connection: typing.Optional[pymysql.connections.Connection]
        :return: number of affected rows, the fetched data and the open database connection
        :rtype: tuple
        :raises TypeError: when the connection is neither None nor a valid Connection
        :raises pymysql.err.OperationalError: when the database connection is closed
        """

        if connection is None:
            connection = pymysql.connect(
                **_config["database"],
                cursorclass=pymysql.cursors.DictCursor
            )

        elif not isinstance(connection, pymysql.connections.Connection):
            raise TypeError("Invalid connection type")

        if connection.open:
            with connection.cursor() as cursor:
                rows = cursor.execute(query, arguments)
                result = list(cursor.fetchall())
        else:
            raise pymysql.err.OperationalError("No open connection")
        return rows, result, connection

    @staticmethod
    def _execute(
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
            rows, result, connection = BackendHelper._execute_no_commit(query, arguments)
            connection.commit()
        finally:
            if connection:
                connection.close()
        return rows, result

    @staticmethod
    def _check_identifier(identifier: int) -> bool:
        """
        Verify that an identifier (internal user ID) is valid

        :param identifier: integer which is used as internal user ID
        :type identifier: int
        :return: True
        :raises TypeError: when the identifier is no integer
        :raises ValueError: when the identifier is not positive
        """

        if not isinstance(identifier, int):
            raise TypeError(f"Expected integer as identifier, not {type(identifier)}")
        if identifier <= 0:
            raise ValueError(f"Expected positive integer as identifier, not {identifier}")
        return True

    @staticmethod
    def _check_location(table: str, column: typing.Optional[str] = None) -> bool:
        """
        Verify that a location (table and optional column) is valid

        :param table: table name in the database
        :type table: str
        :param column: column name in the table
        :type column: typing.Optional[str]
        :return: True
        :raises TypeError: when the table or column is no string
        :raises ValueError: when the table or column is not found in the database
        """

        if not isinstance(table, str):
            raise TypeError(f"Expected string as table name, not {type(table)}")
        if table not in DATABASE_SCHEMA:
            raise ValueError(f"Unknown table name '{table}'")
        if column is None:
            return True

        if not isinstance(column, str):
            raise TypeError(f"Expected string as column name, not {type(table)}")
        if column not in DATABASE_SCHEMA[table]:
            raise ValueError(f"Unknown column '{column}' in table '{table}'")
        return True

    @staticmethod
    def _check_value(value: typing.Union[str, int, bool, None]) -> bool:
        """
        Verify that an identifier (internal user ID) is valid

        :param value: value that should be written somewhere to the database
        :type value: typing.Union[str, int, bool, None]
        :return: True
        :raises TypeError: when the identifier is no integer
        :raises ValueError: when the identifier is not positive
        """

        if isinstance(value, float):
            if value.is_integer():
                value = int(value)
            else:
                raise TypeError("No floats allowed as values")
        if value is not None:
            if not isinstance(value, (str, int, bool)):
                raise TypeError(f"Unsupported type {type(value)} for value {value}")
        return True

    @staticmethod
    def get_value_manually(
            table: str,
            column: typing.Optional[str] = None,
            identifier: typing.Optional[int] = None,
            connection: typing.Optional[pymysql.connections.Connection] = None
    ) -> EXECUTE_NO_COMMIT_TYPE:
        """
        Get the remote value in the column in the table with the identifier but without committing

        If no column name is given, all columns will be fetched (``*``).
        If no identifier is given, the number of fetched rows will not be limited.

        .. note::

            Read the class documentation for :class:`BackendHelper` for more
            information about the functions ending with ``_manually``.


        :param table: name of the table in the database
        :type table: str
        :param column: name of the column in the table (optional)
        :type column: typing.Optional[str]
        :param identifier: internal ID of the record in the given table (optional)
        :type identifier: typing.Optional[int]
        :param connection: optional connection to the database (opened implicitly if None)
        :type connection: typing.Optional[pymysql.connections.Connection]
        :return: number of affected rows and the fetched data
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid
        """

        BackendHelper._check_location(table, column)
        BackendHelper._check_identifier(identifier)

        if column is None:
            if identifier is None:
                return BackendHelper._execute_no_commit(
                    f"SELECT * FROM {table}",
                    connection=connection
                )
            return BackendHelper._execute_no_commit(
                f"SELECT * FROM {table} WHERE id=%s",
                (identifier,),
                connection = connection
            )

        if identifier is None:
            return BackendHelper._execute_no_commit(
                f"SELECT {column} FROM {table}",
                connection = connection
            )
        return BackendHelper._execute_no_commit(
            f"SELECT {column} FROM {table} WHERE id=%s",
            (identifier,),
            connection = connection
        )

    @staticmethod
    def get_value(
        table: str,
        column: typing.Optional[str] = None,
        identifier: typing.Optional[int] = None
    ) -> EXECUTE_TYPE:
        """
        Get the remote value in the column in the table with the identifier

        If no column name is given, all columns will be fetched (``*``).
        If no identifier is given, the number of fetched rows will not be limited.

        :param table: name of the table in the database
        :type table: str
        :param column: name of the column in the table (optional)
        :type column: typing.Optional[str]
        :param identifier: internal ID of the record in the given table (optional)
        :type identifier: typing.Optional[int]
        :return: number of affected rows and the fetched data
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid
        """

        BackendHelper._check_location(table, column)
        BackendHelper._check_identifier(identifier)

        if column is None:
            if identifier is None:
                return BackendHelper._execute(
                    f"SELECT * FROM {table}"
                )
            return BackendHelper._execute(
                f"SELECT * FROM {table} WHERE id=%s",
                (identifier,)
            )

        if identifier is None:
            return BackendHelper._execute(
                f"SELECT {column} FROM {table}"
            )
        return BackendHelper._execute(
            f"SELECT {column} FROM {table} WHERE id=%s",
            (identifier,)
        )

    @staticmethod
    def set_value_manually(
            table: str,
            column: str,
            identifier: int,
            value: typing.Union[str, int, bool, None],
            connection: typing.Optional[pymysql.connections.Connection] = None
    ) -> EXECUTE_NO_COMMIT_TYPE:
        """
        Set the remote value in the column in the table with the identifier but without committing

        Calling this command will check the supplied values and create a
        connection to the database or use the one that was given to
        finally execute the query to set the value in the specified column
        of the specified table. The updated value will not be committed.
        The connection is not closed automatically. This is useful to create
        database transactions. However, you must close the connection to the
        database manually. If this is not your intention, use set_value instead.

        .. note::

            Read the class documentation for :class:`BackendHelper` for more
            information about the functions ending with ``_manually``.


        :param table: name of the table in the database
        :type table: str
        :param column: name of the column in the table
        :type column: str
        :param identifier: internal ID of the record in the given table
        :type identifier: int
        :param value: value to be set for the current user in the specified column
        :type value: typing.Union[str, int, bool, None]
        :param connection: optional connection to the database (opened implicitly if None)
        :type connection: typing.Optional[pymysql.connections.Connection]
        :return: number of affected rows, the fetched data and the open database connection
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid
        """

        BackendHelper._check_value(value)
        BackendHelper._check_identifier(identifier)
        BackendHelper._check_location(table, column)

        return BackendHelper._execute_no_commit(
            f"UPDATE {table} SET {column}=%s WHERE id=%s",
            (value, identifier),
            connection
        )

    @staticmethod
    def set_value(
            table: str,
            column: str,
            identifier: int,
            value: typing.Union[str, int, bool, None]
    ) -> EXECUTE_TYPE:
        """
        Set the remote value in the column in the table with the identifier

        Calling this command will check the supplied values, connect
        to the database and execute the query to set the value
        in the specified column of the specified table. The updated
        value will be committed and the connection closed automatically.
        If this is not your intention, use set_value_manually instead.

        :param table: name of the table in the database
        :type table: str
        :param column: name of the column in the table
        :type column: str
        :param identifier: internal ID of the record in the given table
        :type identifier: int
        :param value: value to be set for the current user in the specified column
        :type value: typing.Union[str, int, bool, None]
        :return: number of affected rows and the fetched data
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid
        """

        BackendHelper._check_value(value)
        BackendHelper._check_identifier(identifier)
        BackendHelper._check_location(table, column)

        return BackendHelper._execute(
            f"UPDATE {table} SET {column}=%s WHERE id=%s",
            (value, identifier)
        )

    @staticmethod
    def set_all_manually(
            table: str,
            column: str,
            value: typing.Union[str, int, bool, None],
            connection: typing.Optional[pymysql.connections.Connection] = None
    ) -> EXECUTE_NO_COMMIT_TYPE:
        """
        Set the remote value in all columns in the table but without committing

        Calling this command will check the supplied values and create a
        connection to the database or use the one that was given to
        finally execute the query to set the value *in all columns*
        of the specified table. The updated value will not be committed.
        The connection is not closed automatically. This is useful to create
        database transactions. However, you must close the connection to the
        database manually. If this is not your intention, use set_all instead.

        .. note::

            Read the class documentation for :class:`BackendHelper` for more
            information about the functions ending with ``_manually``.


        :param table: name of the table in the database
        :type table: str
        :param column: name of the column in the table
        :type column: str
        :param value: value to be set for the current user in the specified column
        :type value: typing.Union[str, int, bool, None]
        :param connection: optional connection to the database (opened implicitly if None)
        :type connection: typing.Optional[pymysql.connections.Connection]
        :return: number of affected rows, the fetched data and the open database connection
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid
        """

        BackendHelper._check_value(value)
        BackendHelper._check_location(table, column)

        return BackendHelper._execute_no_commit(
            f"UPDATE {table} SET {column}=%s",
            (value,),
            connection
        )

    @staticmethod
    def set_all(
            table: str,
            column: str,
            value: typing.Union[str, int, bool, None]
    ) -> EXECUTE_TYPE:
        """
        Set the remote value in all columns in the table

        Calling this command will check the supplied values, connect
        to the database and execute the query to set the value
        *in all columns* of the specified table. The updated
        value will be committed and the connection closed automatically.
        If this is not your intention, use set_all_manually instead.

        :param table: name of the table in the database
        :type table: str
        :param column: name of the column in the table
        :type column: str
        :param value: value to be set for the current user in the specified column
        :type value: typing.Union[str, int, bool, None]
        :return: number of affected rows and the fetched data
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid
        """

        BackendHelper._check_value(value)
        BackendHelper._check_location(table, column)

        return BackendHelper._execute(
            f"UPDATE {table} SET {column}=%s",
            (value,)
        )

    @staticmethod
    def insert_manually(
            table: str,
            values: typing.Dict[str, typing.Union[str, int, bool, None]],
            connection: typing.Optional[pymysql.connections.Connection] = None
    ) -> EXECUTE_NO_COMMIT_TYPE:
        """
        Insert the dictionary of column:value pairs into the table but without committing

        Calling this command will check the supplied values and create
        a connection to the database or use the one that was given to
        finally execute the query to insert the values for the specified
        columns of the specified table. The inserted values will not be committed.
        The connection is not closed automatically. This is useful to create
        database transactions. However, you must close the connection to the
        database manually. If this is not your intention, use insert instead.

        .. note::

            Read the class documentation for :class:`BackendHelper` for more
            information about the functions ending with ``_manually``.


        :param table: name of the table in the database
        :type table: str
        :param values: collection of column:value pairs
        :type values: typing.Dict[str, typing.Union[str, int, bool, None]]
        :param connection: optional connection to the database (opened implicitly if None)
        :type connection: typing.Optional[pymysql.connections.Connection]
        :return: number of affected rows and the fetched data
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid
        """

        for k in values:
            BackendHelper._check_location(table, k)
        for v in values.values():
            BackendHelper._check_value(v)

        return BackendHelper._execute_no_commit(
            f'INSERT INTO {table} ({", ".join(values.keys())}) VALUES ({", ".join(["%s"] * len(values))})',
            tuple(values.values()),
            connection
        )

    @staticmethod
    def insert(
            table: str,
            values: typing.Dict[str, typing.Union[str, int, bool, None]]
    ) -> EXECUTE_TYPE:
        """
        Insert the dictionary of column:value pairs into the table

        Calling this command will check the supplied values, connect
        to the database and execute the query to insert the values
        for the specified columns of the specified table. The new row
        will be committed and the connection closed automatically.
        If this is not your intention, use insert_manually instead.

        :param table: name of the table in the database
        :type table: str
        :param values: collection of column:value pairs
        :type values: typing.Dict[str, typing.Union[str, int, bool, None]]
        :return: number of affected rows and the fetched data
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid
        """

        for k in values:
            BackendHelper._check_location(table, k)
        for v in values.values():
            BackendHelper._check_value(v)

        return BackendHelper._execute(
            f'INSERT INTO {table} ({", ".join(values.keys())}) VALUES ({", ".join(["%s"] * len(values))})',
            tuple(values.values())
        )
