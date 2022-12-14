"""
Data definitions used for unit testing
"""

from typing import List, Optional

# Specify a custom logging configuration for the running API server
# Note: The value must be understood by `logging.config.dictConfig`!
# Setting this variable overwrites the default configuration (default: None)
SERVER_LOGGING_OVERWRITE: Optional[dict] = None

# Set the database URL to be used (default: None) which will be
# passed to SQLAlchemy, so make sure it's understood by SQLAlchemy
# (using None enables the sqlite database instead, see below)
DATABASE_URL: Optional[str] = None

# Default file format for halfway persistent sqlite database files,
# which will be removed after the unittests have completed (the
# placeholders will be filled with the PID and a random nonce)
DATABASE_DEFAULT_FILE_FORMAT: str = "/tmp/unittest_{}_{}.db"

# Default database URL when USE_DATABASE_URL above is not set (the
# placeholder will be filled with the database file location from above)
DATABASE_URL_FORMAT: str = "sqlite:///{}"

# Fallback database URL (in-memory sqlite database) when the persistent sqlite
# file can't be written, which might be the case when the target is not writeable
DATABASE_FALLBACK_URL: str = "sqlite://"

# Enable or disable echoing of commands issued by SQLAlchemy (default: False)
SQLALCHEMY_ECHOING: bool = False

# Command (or path to a script file) that can be used to properly initialize the
# target database to be used by the unittests later, e.g. a script to create the
# database and the database user with the required privileges would be added for
# this field, while nothing will be done when not set (default: None)
# Note: This command will be executed during setup stage of every single unit
# test! Also note that the argument of this field will be used by `subprocess.run`!
# The command won't be executed if a temporary or in-memory sqlite database was used.
COMMAND_INITIALIZE_DATABASE: Optional[List[str]] = None

# Command (or path to a script file) that can be used to properly cleanup the
# target database so that it can be initialized with the above command or script
# afterwards again, e.g. a script to drop the whole database and/or user (default: None)
# Note: This command will be executed during teardown stage of every single unit
# test! Also note that the argument of this field will be used by `subprocess.run`!
# The command won't be executed if a temporary or in-memory sqlite database was used.
COMMAND_CLEANUP_DATABASE: Optional[List[str]] = None

# Maximum number of retries allocating a local port during server startup
MAX_SERVER_START_RETRIES: int = 8

# Maximum number of retries to connect to the API and callback servers during startup
MAX_SERVER_WAIT_RETRIES: int = 10

# Seconds to wait for the API server kill command to complete
API_SUBPROCESS_KILL_TIMEOUT = 0.01

# Seconds to wait for the API server terminate command to complete before killing it
API_SUBPROCESS_TERMINATE_TIMEOUT = 0.1

# Seconds to wait for the API server to start in a single iteration
API_SUBPROCESS_START_WAIT_TIMEOUT = 0.25

# The following values define max limits for the load tests in seconds
LOAD_TEST_INVALID_REQUESTS = 15.0
LOAD_TEST_GET_USERS = 8.0
LOAD_TEST_MAKE_TRANSACTIONS = 30.0
