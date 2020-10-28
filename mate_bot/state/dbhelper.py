"""
MateBot database management helper library
"""

import typing
import logging
import datetime

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


COLUMN_TYPES = typing.Union[int, bool, str, datetime.datetime, None]
QUERY_RESULT_TYPE = typing.List[typing.Dict[str, COLUMN_TYPES]]
EXECUTE_TYPE = typing.Tuple[int, QUERY_RESULT_TYPE]
EXECUTE_NO_COMMIT_TYPE = typing.Tuple[int, QUERY_RESULT_TYPE, pymysql.connections.Connection]


class _CollectionSchema(dict):
    """
    Abstract collection schema base class

    As this is a subclass of the built-in ``dict``, you have full access to all
    methods and features of a standard dictionary. However, this class overwrites
    some of the methods that you would normally expect to work out of the box.

    ``__init__`` will now only accept one dictionary or None as optional parameter.
    The supplied dictionary will be used to create the internal data structure
    (see also ``__setitem__``). Other argument types lead to TypeErrors.

    ``__repr__`` will output the dictionary surrounded by the class name.

    ``__setitem__`` will only accept strings as keys. The values may be
    specified more precisely in a subclass to restrict further usage.
    """

    def __init__(self, obj: typing.Optional[dict] = None):
        if obj is None:
            super().__init__()
        elif isinstance(obj, dict):
            super().__init__()
            for k in obj:
                self[k] = obj[k]
        else:
            raise TypeError("Constructor argument must be dict or None")

    def __repr__(self) -> str:
        return f"{type(self).__name__}({super().__repr__()})"

    def __setitem__(self, key: str, value: typing.Any) -> None:
        if not isinstance(key, str):
            raise TypeError("Key must be str")
        if hasattr(value, "name"):
            if value.name != key:
                raise ValueError(f"Key '{key}' does not match name '{value.name}'")
        super().__setitem__(key, value)


class ColumnSchema:
    """
    Column schema description based on dictionaries to allow easy design validation

    This class functions as a simple container and formatter of the supplied
    values during initialization. Therefore, only ``__repr__`` and ``__str__``
    are defined. While the former is used only for stylistic purposes, the
    later can be used to construct full SQL queries. Look for the method
    :meth:`TableSchema._to_string` on how to use it, because this method calls
    ``str()`` on all columns (type :class:`ColumnSchema`) attached to the table.

    :param name: name of the column in a certain table
    :type name: str
    :param data_type: SQL name of the data type (e.g. ``"BOOLEAN"``)
    :type data_type: str
    :param null: switch whether ``NULL`` values are allowed in the column
    :type null: bool
    :param extras: string of extra SQL parameters for column creation (e.g. ``"UNIQUE"``)
    :type extras: typing.Optional[str]
    """

    def __init__(self, name: str, data_type: str, null: bool, extras: typing.Optional[str] = None):
        if not isinstance(name, str):
            raise TypeError(f"Expected str as name, not {type(name)}")
        if not isinstance(data_type, str):
            raise TypeError(f"Expected str as data type, not {type(name)}")
        if not isinstance(null, bool):
            raise TypeError(f"Expected bool as null switch, not {type(name)}")
        if extras is not None:
            if not isinstance(extras, str):
                raise TypeError(f"Expected str for the extras, not {type(name)}")

        self.name: str = name
        self.data_type: str = data_type
        self.null: bool = null
        self.extras: typing.Optional[str] = extras

    def __repr__(self) -> str:
        return f"ColumnSchema({self.name} <{self.data_type}>)"

    def __str__(self) -> str:
        string = f"`{self.name}` {self.data_type}"
        if not self.null:
            string = f"{string} NOT NULL"
        if self.extras is not None:
            string = f"{string} {self.extras}"
        return string


class ReferenceSchema:
    """
    Reference schema description based on dictionaries to allow easy design validation

    A reference describes that a key in the current table is a foreign key of another table.

    This class functions as a simple container and formatter of the supplied
    values during initialization. Therefore, only ``__repr__`` and ``__str__``
    are defined. While the former is used only for stylistic purposes, the
    later can be used to construct full SQL queries. Look for the method
    :meth:`TableSchema._to_string` on how to use it, because this method calls
    ``str()`` on all references (type :class:`ReferenceSchema`) attached to the table.
    """

    def __init__(self, local_name: str, ref_table: str, ref_name: str, cascade: bool = True):
        self.local_name: str = local_name
        self.ref_table: str = ref_table
        self.ref_name: str = ref_name
        self.cascade: bool = cascade

    def __repr__(self) -> str:
        return f"ReferenceSchema({self.local_name}, {self.ref_table}[{self.ref_name}])"

    def __str__(self) -> str:
        string = f"FOREIGN KEY ({self.local_name}) REFERENCES {self.ref_table}({self.ref_name})"
        if self.cascade:
            string = f"{string} ON DELETE CASCADE"
        return string


class TableSchema(_CollectionSchema):
    """
    Table schema description based on dictionaries to allow easy design validation

    As this is a subclass of the built-in ``dict``, you have full
    access to all methods and features of a standard dictionary.

    Besides the methods that have been overwritten in :class:`_CollectionSchema`,
    this class overwrites the following other methods:

    * ``__init__`` takes a name (``str``), a dictionary of pairs of ``str`` and
      :class:`ColumnSchema` and a list of references (type :class:`ReferenceSchema`).

    * ``__contains__`` uses improved checks to validate if a certain column
      name (type ``str`` and key of the underlying dictionary), a certain
      :class:`ColumnSchema` object (values in the underlying dictionary) or
      a certain :class:`ReferenceSchema` object is part of the table.

    * ``__setitem__`` checks if the supplied key is of type ``str``
      and the supplied value is a :class:`ColumnSchema` object. Other
      types for the keys or values lead to TypeError exceptions.

    * ``__str__`` calls :meth:`_to_string` with the indentation ``4`` internally.

    :param name: name of the table in the database
    :type name: str
    :param columns: predefined set of columns for this table
    :type columns: typing.Dict[str, ColumnSchema],
    :param refs: list of references to columns in other tables
    :type refs: typing.Optional[typing.List[ReferenceSchema]]
    """

    def __init__(
            self,
            name: str,
            columns: typing.Dict[str, ColumnSchema],
            refs: typing.Optional[typing.List[ReferenceSchema]] = None
    ):
        if not isinstance(name, str):
            raise TypeError(f"Expected str as name, not {type(name)}")
        if not isinstance(columns, dict):
            raise TypeError(f"Expected dictionary, not {type(columns)}")
        if refs is not None:
            if not isinstance(refs, list):
                raise TypeError(f"Expected list for references, not {type(refs)}")

        super().__init__(columns)
        self.name: str = name
        if refs is None:
            self.refs: typing.Optional[typing.List[ReferenceSchema]] = []
        else:
            self.refs: typing.Optional[typing.List[ReferenceSchema]] = refs.copy()

    def __contains__(self, item: typing.Union[str, ColumnSchema, ReferenceSchema]) -> bool:
        if isinstance(item, ColumnSchema):
            return super().__contains__(item)
        if isinstance(item, ReferenceSchema):
            return item in self.refs
        if isinstance(item, str):
            return item in self.keys()
        return False

    def __setitem__(self, key: str, value: ColumnSchema) -> None:
        if not isinstance(value, ColumnSchema):
            raise TypeError(f"Expected ColumnSchema as type, not {type(value)}")
        super().__setitem__(key, value)

    def __str__(self) -> str:
        return self._to_string(4)

    def _to_string(self, indent: int) -> str:
        """
        Generate a fully formatted SQL query string that can be used to create this table

        :param indent: number of spaces for indentation of the column definitions
            (use ``0`` to disable line breaks and indents completely)
        :type indent: int
        :return: fully formatted string that can be used as SQL query string to create the table
        :rtype: str
        """

        sep, conjunction = "\n", ",\n"
        if indent == 0:
            sep, conjunction = "", ", "
        entries = conjunction.join(
            [f"{' ' * abs(indent)}{str(k)}" for k in list(self.values()) + list(self.refs)]
        )
        return f"CREATE TABLE {self.name} ({sep}{entries}{sep});"


class DatabaseSchema(_CollectionSchema):
    """
    Database schema description based on dictionaries to allow easy design validation

    As this is a subclass of the built-in ``dict``, you have full
    access to all methods and features of a standard dictionary.

    Besides the methods that have been overwritten in :class:`_CollectionSchema`,
    this class overwrites ``__contains__`` for better checks if a table
    (:class:`TableSchema`) is in the database. Additionally, this class overwrites
    ``__setitem__`` to check if the supplied value is an instance of the
    class :class:`TableSchema`. Other values lead to TypeErrors.
    """

    def __contains__(self, item: typing.Any) -> bool:
        if isinstance(item, TableSchema):
            return item in self.values()
        return super().__contains__(item)

    def __setitem__(self, key: str, value: TableSchema) -> None:
        if not isinstance(value, TableSchema):
            raise TypeError
        super().__setitem__(key, value)


DATABASE_SCHEMA = DatabaseSchema({
    "users": TableSchema(
        "users",
        {
            "id": ColumnSchema(
                "id", "INT", False,
                "PRIMARY KEY AUTO_INCREMENT"
            ),
            "tid": ColumnSchema(
                "tid", "BIGINT", True,
                "UNIQUE"
            ),
            "username": ColumnSchema("username", "VARCHAR(255)", True),
            "name": ColumnSchema("name", "VARCHAR(255)", False),
            "balance": ColumnSchema(
                "balance", "MEDIUMINT", False,
                "DEFAULT 0"
            ),
            "permission": ColumnSchema(
                "permission", "BOOLEAN", False,
                "DEFAULT false"
            ),
            "active": ColumnSchema(
                "active", "BOOLEAN", False,
                "DEFAULT true"
            ),
            "created": ColumnSchema(
                "created", "TIMESTAMP", False,
                "DEFAULT CURRENT_TIMESTAMP"
            ),
            "accessed": ColumnSchema(
                "accessed", "TIMESTAMP", False,
                "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            )
        }
    ),
    "transactions": TableSchema(
        "transactions",
        {
            "id": ColumnSchema(
                "id", "INT", False,
                "PRIMARY KEY AUTO_INCREMENT"
            ),
            "sender": ColumnSchema("sender", "INT", False),
            "receiver": ColumnSchema("receiver", "INT", False),
            "amount": ColumnSchema("amount", "MEDIUMINT", False),
            "reason": ColumnSchema("reason", "VARCHAR(255)", True),
            "registered": ColumnSchema(
                "registered", "TIMESTAMP", False,
                "DEFAULT CURRENT_TIMESTAMP"
            )
        },
        [
            ReferenceSchema("sender", "users", "id", True),
            ReferenceSchema("receiver", "users", "id", True)
        ]
    ),
    "collectives": TableSchema(
        "collectives",
        {
            "id": ColumnSchema(
                "id", "INT", False,
                "PRIMARY KEY AUTO_INCREMENT"
            ),
            "active": ColumnSchema(
                "active", "BOOLEAN", False,
                "DEFAULT true"
            ),
            "amount": ColumnSchema("amount", "MEDIUMINT", False),
            "externals": ColumnSchema("externals", "SMALLINT", True),
            "description": ColumnSchema("description", "VARCHAR(255)", True),
            "communistic": ColumnSchema("communistic", "BOOLEAN", False),
            "creator": ColumnSchema("creator", "INT", False),
            "created": ColumnSchema(
                "created", "TIMESTAMP", False,
                "DEFAULT CURRENT_TIMESTAMP"
            )
        },
        [
            ReferenceSchema("creator", "users", "id", True)
        ]
    ),
    "collectives_users": TableSchema(
        "collectives_users",
        {
            "id": ColumnSchema(
                "id", "INT", False,
                "PRIMARY KEY AUTO_INCREMENT"
            ),
            "collectives_id": ColumnSchema("collectives_id", "INT", False),
            "users_id": ColumnSchema("users_id", "INT", False),
            "vote": ColumnSchema("vote", "BOOLEAN", False)
        },
        [
            ReferenceSchema("collectives_id", "collectives", "id", True),
            ReferenceSchema("users_id", "users", "id", True)
        ]
    ),
    "collective_messages": TableSchema(
        "collective_messages",
        {
            "id": ColumnSchema(
                "id", "INT", False,
                "PRIMARY KEY AUTO_INCREMENT"
            ),
            "collectives_id": ColumnSchema("collectives_id", "INT", False),
            "chat_id": ColumnSchema("chat_id", "BIGINT", False),
            "msg_id": ColumnSchema("msg_id", "INT", False)
        },
        [
            ReferenceSchema("collectives_id", "collectives", "id", True)
        ]
    ),
    "externals": TableSchema(
        "externals",
        {
            "id": ColumnSchema(
                "id", "INT", False,
                "PRIMARY KEY AUTO_INCREMENT"
            ),
            "internal": ColumnSchema("internal", "INT", True),
            "external": ColumnSchema(
                "external", "INT", False,
                "UNIQUE"
            ),
            "changed": ColumnSchema(
                "changed", "TIMESTAMP", False,
                "DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"
            )
        },
        [
            ReferenceSchema("internal", "users", "id", True),
            ReferenceSchema("external", "users", "id", True)
        ]
    )
})


class BackendHelper:
    """
    Helper class providing easy methods to read and write values in the database

    Instead of direct calls to the database using :func:`_execute`, this
    class provides a collection of static methods that make it easy
    to interact with the database as you don't need to know about the
    actual database query language. Any high level implementation
    may subclass this class in order to declare its area of usage.

    Use the functions ending with ``_manually`` in case you need more
    than one call to the functions defined here to fulfill your needs.
    All your queries will be cached on the server side as long as you don't
    call the ``.commit()`` method on the returned ``Connection`` object
    to save the changes you introduced during your previous queries.

    .. warning::

        Important! When the program exits or the connection is closed
        without calling ``.commit()``, the introduced changes are lost!
        So, be careful and enclose this call in a try-finally-block:

        .. code-block:: python3

                connection = None
                try:
                    rows, result, connection = BackendHelper._execute_no_commit(...)
                    ...
                    connection.commit()
                finally:
                    if connection:
                        connection.close()

    .. note::

        In order to use the :class:`BackendHelper` class properly, you need
        to set the class attribute :attr:`db_config`. It expects a dictionary
        that can be extracted to valid keyword arguments for the ``connect``
        function of the used database module as long as this module fulfills
        `the Database API Specification v2 <https://www.python.org/dev/peps/pep-0249/>`_.

    The class :class:`BackendHelper` provides two further class attributes.
    :attr:`schema` holds a reference to the module's ``DATABASE_SCHEMA`` object
    (type :class:`DatabaseSchema`). The :attr:`query_logger` class attribute is ``None``
    by default but expects a :class:`logging.Logger` object. Every attempted SQL
    query will produce a log message with level *DEBUG* if a logger has been found.
    """

    db_config: dict = {}
    """
    Database configuration that must be valid for extraction in the ``connect``
    function of the used database module as long as this module fulfills the
    `Database API Specification v2 <https://www.python.org/dev/peps/pep-0249/>`_.
    If it doesn't, the program would not be able to operate properly, anyway.
    """

    query_logger: typing.Optional[logging.Logger] = None
    """Logger that creates a ``DEBUG`` record for every query sent to the database."""

    schema: DatabaseSchema = DATABASE_SCHEMA
    """
    Database schema that is used to validate incoming queries before actually
    performing them. This is a security measure to circumvent SQL injections.
    Note that the database may be created completely from scratch, only based
    on this specified schema. Use :func:`rebuild_database` for this purpose.
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

        if isinstance(BackendHelper.query_logger, logging.Logger):
            try:
                BackendHelper.query_logger.debug(f"Executing '{query}' using args {arguments}")
            except AttributeError:
                pass

        if connection is None:
            connection = pymysql.connect(
                **BackendHelper.db_config,
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
        if table not in BackendHelper.schema:
            raise ValueError(f"Unknown table name '{table}'")
        if column is None:
            return True

        if not isinstance(column, str):
            raise TypeError(f"Expected string as column name, not {type(table)}")
        if column not in BackendHelper.schema[table]:
            raise ValueError(f"Unknown column '{column}' in table '{table}'")
        return True

    @staticmethod
    def _check_key_location(table: str, key: str) -> bool:
        """
        Verify that a location (table and column) is valid and the column is a unique key

        :param table: table name in the database
        :type table: str
        :param key: column name that should be used as unique key for a query
        :type key: str
        :return: whether the column can be used as a unique key in the table
        :rtype: bool
        :raises TypeError: when the table or column is no string
        :raises ValueError: when the table or column is not found in the database
        """

        BackendHelper._check_location(table, key)
        extras = BackendHelper.schema[table][key].extras
        if extras is not None:
            return "PRIMARY KEY" in extras.upper() or "UNIQUE" in extras.upper()
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
    def rebuild_database() -> bool:
        """
        Rebuild the database from scratch, deleting all stored data **without recovery**

        .. warning::

            Using this command will delete all data currently stored in the configured
            database without further asking. It will then install the new database
            layout based on the supplied :attr:`schema` class attribute. Note that
            there is no way to recover the previously stored data afterwards.

        If the :class:`BackendHelper` has a class attribute :attr:`query_logger`, it
        will be used to create some more log messages, some of them with higher
        logging levels than just `DEBUG`. It's recommended to set the logger before
        calling this command because it might help tracking down problems and errors.

        :return: success of the operation
        :rtype: bool
        """

        def _log(level, msg, **kwargs):
            if isinstance(BackendHelper.query_logger, logging.Logger):
                try:
                    BackendHelper.query_logger.log(level, msg, **kwargs)
                except AttributeError:
                    pass

        _log(logging.WARNING, "Attention: Rebuilding the database...")

        error = False
        try:
            db_name = BackendHelper.db_config["db"]
            del BackendHelper.db_config["db"]

            rows, result = BackendHelper._execute("SHOW DATABASES")
            _log(logging.DEBUG, f"Found {rows} databases on the server.")

            if any([db_name in r.values() for r in result]):
                _log(logging.INFO, f"Deleting old table '{db_name}'...")
                BackendHelper._execute(f"DROP DATABASE {db_name}")
            BackendHelper._execute(f"CREATE DATABASE {db_name}")

            BackendHelper.db_config["db"] = db_name

            _log(logging.DEBUG, "Creating tables...")
            for k in BackendHelper.schema:
                BackendHelper._execute(BackendHelper.schema[k]._to_string(0))

        except pymysql.err.MySQLError as err:
            error = True
            _log(logging.ERROR, f"Error while rebuilding database: {err}", exc_info=True)

        return not error

    @staticmethod
    def get_values_by_key_manually(
            table: str,
            key: str,
            identifier: typing.Union[int, bool, str],
            connection: typing.Optional[pymysql.connections.Connection] = None
    ) -> EXECUTE_NO_COMMIT_TYPE:
        """
        Get all remote values in the table with the identifier used for the key but without committing

        The value for ``key`` must be a valid column name and the column must be marked
        as unique or primary key for the table. Otherwise, a ValueError will be raised.

        .. note::

            Read the class documentation for :class:`BackendHelper` for more
            information about the functions ending with ``_manually``.


        :param table: name of the table in the database
        :type table: str
        :param key: name of the column in the table that should be used as unique key
        :type key: str
        :param identifier: unique identifier of the record in the table
        :type identifier: typing.Union[int, bool, str]
        :param connection: optional connection to the database (opened implicitly if None)
        :type connection: typing.Optional[pymysql.connections.Connection]
        :return: number of affected rows and the fetched data
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid or the key column is not unique
        """

        if not BackendHelper._check_key_location(table, key):
            raise ValueError(f"Column {key} is not unique in the table {table}")
        if not isinstance(identifier, (int, bool, str)):
            raise TypeError(f"Unexpected type {type(identifier)} as identifier")

        return BackendHelper._execute_no_commit(
            f"SELECT * FROM {table} WHERE {key}=%s",
            (identifier,),
            connection=connection
        )

    @staticmethod
    def get_values_by_key(
            table: str,
            key: str,
            identifier: typing.Union[int, bool, str]
    ) -> EXECUTE_TYPE:
        """
        Get all remote values in the table with the identifier used for the key

        The value for ``key`` must be a valid column name and the column must be marked
        as unique or primary key for the table. Otherwise, a ValueError will be raised.

        :param table: name of the table in the database
        :type table: str
        :param key: name of the column in the table that should be used as unique key
        :type key: str
        :param identifier: unique identifier of the record in the table
        :type identifier: typing.Union[int, bool, str]
        :return: number of affected rows and the fetched data
        :rtype: tuple
        :raises TypeError: when an invalid type was found
        :raises ValueError: when a value is not valid or the key column is not unique
        """

        if not BackendHelper._check_key_location(table, key):
            raise ValueError(f"Column {key} is not unique in the table {table}")
        if not isinstance(identifier, (int, bool, str)):
            raise TypeError(f"Unexpected type {type(identifier)} as identifier")

        return BackendHelper._execute(
            f"SELECT * FROM {table} WHERE {key}=%s",
            (identifier,)
        )

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
        if identifier is not None:
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

    @staticmethod
    def extract_all(ignore_schema: bool = False) -> typing.Dict[str, QUERY_RESULT_TYPE]:
        """
        Extract all data stored in the current database, sorted by table

        :param ignore_schema: switch whether the schema of the database should be ignored
        :type ignore_schema: bool
        :return: all data stored in the database
        """

        tables = BackendHelper._execute("SHOW TABLES")[1]
        BackendHelper.query_logger.debug(f"Found {len(tables)} tables in the database.")
        tables = [list(t.values())[0] for t in tables]
        BackendHelper.query_logger.debug(f"Table names: {', '.join(tables)}")

        result = {}
        for t in tables:
            if not ignore_schema:
                try:
                    result[t] = BackendHelper.get_value(t)[1]
                except ValueError:
                    BackendHelper.query_logger.error(
                        f"The table {t} could not be extracted. It might "
                        "conflict with the database schema definition?"
                    )
            else:
                result[t] = BackendHelper._execute(f"SELECT * FROM {t}")
        return result
