#!/usr/bin/env python3

import os
import sys
import json
import getpass
import secrets
import argparse
import logging.config
from typing import List, Optional
from collections import OrderedDict

import uvicorn
import alembic.config
import sqlalchemy.exc

from matebot_core import settings as _settings
from matebot_core.api import auth
from matebot_core.api.api import create_app
from matebot_core.persistence import database, models


DEFAULT_COMMUNITY_NAME = "Community"


def get_parser(program: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=program)

    commands = parser.add_subparsers(
        description="Available sub-commands: init, apps*, users*, run, systemd, auto",
        dest="command",
        required=True,
        metavar="<command>",
        help="the sub-command to be executed (some have their own subcommands, too)"
    )

    parser_init = commands.add_parser(
        "init",
        description="Initialize the project by creating config files and some database models"
    )

    parser_apps = commands.add_parser(
        "apps",
        description="Manage registered API applications"
    )
    app_command = parser_apps.add_subparsers(
        description="Available actions: show, add, del",
        dest="action",
        metavar="<action>",
        required=True,
        help="action to perform for apps"
    )
    parser_apps_show = app_command.add_parser(
        "show",
        description="Show a list of currently registered applications"
    )
    parser_apps_add = app_command.add_parser(
        "add",
        description="Add a new application with a password for the login & authentication process"
    )
    parser_apps_del = app_command.add_parser(
        "del",
        description="Delete an existing application to block further API access"
    )

    parser_users = commands.add_parser(
        "users",
        description="Manage API end users"
    )
    user_command = parser_users.add_subparsers(
        description="Available actions: show, update",
        dest="action",
        metavar="<action>",
        required=True,
        help="action to perform for users"
    )
    parser_users_show = user_command.add_parser(
        "show",
        description="Show a list of all users"
    )
    parser_users_update = user_command.add_parser(
        "update",
        description="Update a user's flags (note that those operations may be "
                    "rejected if not applicable; also note that externals "
                    "with voucher can't become internals by this command)"
    )

    parser_run = commands.add_parser(
        "run",
        description="Run 'uvicorn' ASGI server to serve the MateBot core REST API"
    )

    parser_systemd = commands.add_parser(
        "systemd",
        description="Create a systemd unit file to run the MateBot core REST API as system service"
    )

    parser_init.add_argument(
        "--database",
        type=str,
        metavar="url",
        help="Database connection URL including scheme and auth"
    )
    parser_init.add_argument(
        "--community-name",
        type=str,
        metavar="name",
        help=f"Globally unique username of the community user "
             f"(default: '{os.environ.get('COMMUNITY_NAME', DEFAULT_COMMUNITY_NAME)}')"
    )
    parser_init.add_argument(
        "--no-community",
        action="store_true",
        help="Don't create the community user if it doesn't exist (not recommended)"
    )
    parser_init.add_argument(
        "--no-migrations",
        action="store_true",
        help="Do not apply migrations automatically (not recommended)"
    )

    parser_apps_show.add_argument(
        "--json",
        action="store_true",
        help="Print the result in JSON format instead of human-readable text"
    )
    parser_apps_show.add_argument(
        "--indent",
        type=int,
        metavar="n",
        help="(JSON-only) Indent the JSON response with n spaces (default: none)"
    )

    parser_apps_add.add_argument(
        "--app",
        type=str,
        metavar="name",
        required=True,
        help="Name of the newly created application account"
    )
    parser_apps_add.add_argument(
        "--password",
        type=str,
        metavar="passwd",
        help="Password for the new app account (will be asked interactively if omitted)"
    )

    parser_apps_del.add_argument(
        "app",
        metavar="name/ID",
        help="name or ID of the application that should be deleted"
    )

    parser_users_show.add_argument(
        "--json",
        action="store_true",
        help="Print the result in JSON format instead of human-readable text"
    )
    parser_users_show.add_argument(
        "--indent",
        type=int,
        metavar="n",
        help="(JSON-only) Indent the JSON response with n spaces (default: none)"
    )

    parser_users_update.add_argument(
        "identifier",
        metavar="ID",
        type=int,
        help="Unique ID to identify the user"
    )
    parser_users_update.add_argument(
        "level",
        metavar="level",
        choices=("unchanged", "external", "internal", "privileged"),
        help="Permission level for the targeted user (choices: 'unchanged', 'external', 'internal', 'privileged')"
    )

    parser_run.add_argument(
        "--host",
        type=str,
        metavar="host",
        help="Bind TCP socket to this host (overwrite config)"
    )
    parser_run.add_argument(
        "--port",
        type=int,
        metavar="port",
        help="Bind TCP socket to this port (overwrite config)"
    )
    parser_run.add_argument(
        "--config",
        type=str,
        metavar="config",
        default="config.json",
        help="Overwrite the config file (defaults to 'config.json')"
    )
    parser_run.add_argument(
        "--debug",
        action="store_true",
        help="Enable full debug mode including tracebacks via HTTP (probably insecure)"
    )
    parser_run.add_argument(
        "--debug-sql",
        action="store_true",
        help="Enable echoing of database actions (overwrites config)"
    )
    parser_run.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload"
    )
    parser_run.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="n",
        help="Number of worker processes (not valid with --reload)",
    )
    parser_run.add_argument(
        "--no-access-log",
        action="store_true",
        help="Disable access logs"
    )
    parser_run.add_argument(
        "--use-colors",
        action="store_true",
        help="Enable colorized output (may break file logs!)"
    )
    parser_run.add_argument(
        "--root-path",
        type=str,
        default="",
        metavar="p",
        help="Sub-mount the application below the given path"
    )

    parser_systemd.add_argument(
        "--force",
        action="store_true",
        help="Allow overwriting existing files"
    )
    parser_systemd.add_argument(
        "--path",
        type=str,
        default=os.path.join(os.path.abspath("."), "matebot_core.service"),
        metavar="p",
        help="Path to the newly created systemd file"
    )

    parser_auto = commands.add_parser(
        "auto",
        description="Deploy and start the server in 'auto mode' using environment variables for first configuration"
    )
    parser_auto.add_argument(
        "--host",
        type=str,
        metavar="host",
        help="Bind TCP socket to this host (overwrite config and environment)"
    )
    parser_auto.add_argument(
        "--port",
        type=int,
        metavar="port",
        help="Bind TCP socket to this port (overwrite config and environment)"
    )
    parser_auto.add_argument(
        "--debug-sql",
        action="store_true",
        help="Enable echoing of database actions (overwrite config and environment)"
    )
    parser_auto.add_argument(
        "--root-path",
        type=str,
        default="",
        metavar="p",
        help="Sub-mount the application below the given path"
    )

    return parser


def handle_systemd(args: argparse.Namespace) -> int:
    python_executable = sys.executable
    if sys.executable is None or sys.executable == "":
        python_executable = "python3"
        print(
            "Revise the 'ExecStart' parameter, since the Python "
            "interpreter path could not be determined reliably.",
            file=sys.stderr
        )

    if not os.path.exists("matebot_core"):
        print("Path 'matebot_core' not found!", file=sys.stderr)
        return 1

    content = f"""[Unit]
Description=MateBot core REST API server
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
ExecStart={python_executable} -m matebot_core run
User={getpass.getuser()}
WorkingDirectory={os.path.abspath(".")}
Restart=always
SyslogIdentifier=matebot_core

[Install]
WantedBy=multi-user.target
"""

    if os.path.exists(args.path) and not args.force:
        print(f"File {args.path!r} already exists. Aborting!", file=sys.stderr)
        return 1

    with open(args.path, "w") as f:
        f.write(content)

    print(
        f"Successfully created the new file {args.path!r}. Now, create a "
        f"symlink from /lib/systemd/system/ to that file. Then use 'systemctl "
        f"daemon-reload' and enable your new service. Check that it works afterwards."
    )

    return 0


def run_server(args: argparse.Namespace):
    if args.debug:
        print("Do not start the server this way during production!", file=sys.stderr)

    _settings.CONFIG_PATHS.insert(0, args.config)
    try:
        settings = _settings.Settings()
    except ValueError:
        print("Ensure that the configuration file is valid. Please correct any errors.", file=sys.stderr)
        raise

    if args.debug:
        settings.logging.root["level"] = "DEBUG"
        for handler in settings.logging.handlers:
            settings.logging.handlers[handler]["level"] = "DEBUG"
    if args.debug_sql:
        settings.database.debug_sql = args.debug_sql

    port = args.port
    if port is None:
        port = settings.server.port
    host = args.host
    if host is None:
        host = settings.server.host

    app = create_app(settings=settings)

    logging.getLogger("matebot_core").info(f"Server running at host {host} port {port}")
    uvicorn.run(
        "matebot_core.api:api.app" if args.reload else app,
        port=port,
        host=host,
        reload=args.reload,
        workers=args.workers,
        log_level="debug" if args.debug else "info",
        log_config=settings.logging.dict(),
        access_log=not args.no_access_log,
        use_colors=args.use_colors,
        proxy_headers=True,
        root_path=args.root_path
    )


def _setup_config(db: Optional[str] = None, init: bool = False) -> _settings.Settings:
    try:
        _settings.INTERACTIVE_MODE = init
        settings = _settings.Settings()
    except RuntimeError as exc:
        if init:
            print("No settings file found. A basic config will be created now.")
        settings = _settings.read_settings_from_json_source(create=True)

        if db:
            settings["database"]["connection"] = db
        elif not init:
            raise RuntimeError("Non-interactive mode without 'db' argument is invalid") from exc
        else:
            print(
                "\nEnter the full database connection string below. It's required to make the "
                "project persistent. It uses an in-memory sqlite3 database by default (press "
                "Enter to use that default). Note that the in-memory database does not work "
                "properly in all environments. A persistent database is highly recommended."
            )
            settings["database"]["connection"] = input("> ") or settings["database"]["connection"]

        with open(_settings.CONFIG_PATHS[0], "w") as f:
            json.dump(settings, f, indent=4)
        settings = _settings.Settings()
    else:
        if init:
            print(
                "A config file has been found and will be used. If you want a fresh installation, "
                "you should remove the config file and clear the database, then run this command again."
            )
    finally:
        _settings.INTERACTIVE_MODE = True
    return settings


def init_project(args: argparse.Namespace, no_db_init: bool = False, no_hint: bool = False) -> int:
    settings = _setup_config(args.database or os.environ.get("DATABASE_CONNECTION", None), not (no_db_init or no_hint))
    config = settings
    if not args.no_migrations:
        alembic.config.main(argv=["upgrade", "head"])
    if not no_db_init:
        database.init(config.database.connection, config.database.debug_sql, create_all=False)
    session = database.get_new_session()

    try:
        session.query(models.User).all()
    except sqlalchemy.exc.DatabaseError:
        print(
            "No table 'users' found in the database. Please initialize the database first. "
            "Perform the necessary database migrations using the 'alembic upgrade head' command .",
            file=sys.stderr
        )
        return 1

    if not args.no_community:
        specials = session.query(models.User).filter_by(special=True).all()
        if len(specials) > 1:
            raise RuntimeError("Multiple community users found. Please drop a bug report.")
        if len(specials) == 0:
            name = args.community_name
            if args.community_name is None:
                default_name = os.environ.get('COMMUNITY_NAME', DEFAULT_COMMUNITY_NAME)
                print(
                    "No community username has been specified! The default value "
                    f"{default_name!r} will be used. This value can be changed "
                    f"later via the API using the 'POST /v1/users/setName' endpoint.",
                    file=sys.stderr
                )
                name = default_name
            session.add(models.User(
                name=name,
                active=True,
                special=True,
                external=False,
                permission=False
            ))
            session.commit()
            session.flush()

    if len(session.query(models.Application).all()) == 0 and not no_hint:
        print(
            "\nThere's no registered application yet. Nobody can use the API "
            "without an application account, because the authentication procedure "
            "makes use of those accounts. Re-run this utility with the 'add-app' "
            "option to add new application accounts to the database to be "
            "able to login to the API via application name and password."
        )

    session.close()
    if not no_hint:
        print("Done.")
    return 0


def print_table(objs: List[dict], keys: Optional[List[str]] = None):
    info = OrderedDict()
    if keys:
        for k in keys:
            info[k] = len(k)
    for obj in objs:
        for key in obj:
            if keys and key not in keys:
                continue
            if key not in info:
                info[key] = len(key)
            info[key] = max(len(str(obj.get(key))), info.get(key))
    print(" | ".join([f"{k:<{info[k]}}" for k in info]))
    print("-+-".join(["-" * info[k] for k in info]))
    for obj in objs:
        print(" | ".join([f"{obj[k]!s:<{info[k]}}" for k in info]))


def show_apps(args: argparse.Namespace) -> int:
    config = _settings.Settings()
    database.init(config.database.connection, config.database.debug_sql)
    with database.get_new_session() as session:
        applications = session.query(models.Application).all()

        if args.json:
            print(json.dumps([app.schema.dict() for app in applications], indent=args.indent))
            return 0
        print_table([app.schema.dict() for app in applications], ["id", "name", "created"])
    return 0


def add_app(args: argparse.Namespace) -> int:
    if not args.app:
        print("Empty app names are not allowed.", file=sys.stderr)
        return 1

    config = _settings.config.CoreConfig(**_settings.read_settings_from_json_source(False))
    database.init(config.database.connection, config.database.debug_sql)
    session = database.get_new_session()

    if session.query(models.Application).filter_by(name=args.app).all():
        print(
            f"An application with the given name {args.app!r} already "
            f"exists. Therefore, it can't be created. Exiting.",
            file=sys.stderr
        )
        session.flush()
        session.close()
        return 1

    passwd = args.password or getpass.getpass()
    if not passwd:
        print("A password is mandatory. No new application account created!", file=sys.stderr)
        return 1
    elif args.app and passwd:
        salt = secrets.token_urlsafe(16)
        session.add(models.Application(name=args.app, password=auth.hash_password(passwd, salt), salt=salt))
        session.commit()
        print(f"Successfully created new application {args.app!r}.")
        return 0


def del_app(args: argparse.Namespace) -> int:
    app = args.app
    config = _settings.config.CoreConfig(**_settings.read_settings_from_json_source(False))
    database.init(config.database.connection, config.database.debug_sql)
    session = database.get_new_session()

    try:
        app = int(app)
        application = session.query(models.Application).get(app)
        if application is None:
            print(f"There's no application with the ID {app} in the database!", file=sys.stderr)
            return 1

    except ValueError:
        applications = session.query(models.Application).filter_by(name=app).all()
        if len(applications) == 0:
            print(f"There's no application with name {app!r} in the database!", file=sys.stderr)
            return 1
        elif len(applications) > 1:
            print(f"The application name {app} is not unambiguous! Please use the app ID.", file=sys.stderr)
            return 1
        application = applications[0]

    session.delete(application)
    session.commit()
    print(
        f"Successfully deleted application named {application.name!r} (ID {application.id}). "
        f"Further login won't be possible. You should restart the server process in order to "
        f"forcefully invalidate the access token the application might have stored."
    )
    return 0


def handle_apps(args: argparse.Namespace) -> int:
    return {
        "show": show_apps,
        "add": add_app,
        "del": del_app
    }[args.action](args)


def show_users(args: argparse.Namespace) -> int:
    def _conv(d: dict) -> dict:
        d["aliases"] = len(d["aliases"])
        d["voucher"] = d["voucher_id"]
        return d

    config = _settings.Settings()
    database.init(config.database.connection, config.database.debug_sql)
    with database.get_new_session() as session:
        users = session.query(models.User).all()

        if args.json:
            print(json.dumps([user.schema.dict() for user in users], indent=args.indent))
            return 0
        print_table(
            [_conv(user.schema.dict()) for user in users],
            ["id", "name", "balance", "active", "external", "permission", "voucher", "aliases"]
        )
    return 0


def update_user(args: argparse.Namespace) -> int:
    config = _settings.Settings()
    database.init(config.database.connection, config.database.debug_sql)
    with database.get_new_session() as session:
        user: Optional[models.User] = session.query(models.User).get(args.identifier)
        if user is None:
            print(f"No user with identifier {args.identifier} has been found!")
            return 1

        if args.level == "unchanged":
            print("No modification has been requested.")
            return 0
        elif not user.active:
            print("This user can't be updated, since it has been softly deleted.")
            return 0
        elif args.level == "external":
            if user.vouching_for:
                print(f"This user can't be updated, since it vouches for {len(user.vouching_for)} others.")
                return 1
            user.external = True
            user.permission = False
            user.voucher_id = None
        elif args.level == "internal":
            if user.voucher_id is not None:
                print(f"User {user.voucher_id} has previously vouched for {user.name!r}. This will be reset.")
            user.external = False
            user.permission = False
            user.voucher_id = None
        elif args.level == "privileged":
            if user.voucher_id is not None:
                print(f"User {user.voucher_id} has previously vouched for {user.name!r}. This will be reset.")
            user.external = False
            user.permission = True
            user.voucher_id = None
        session.add(user)
        session.commit()
        print(f"Successfully updated user {user.id} named {user.name!r}!")

    return 0


def handle_users(args: argparse.Namespace) -> int:
    return {
        "show": show_users,
        "update": update_user
    }[args.action](args)


def run_in_auto_mode(args: argparse.Namespace) -> int:
    logger = logging.getLogger("auto")

    # Setup the configuration
    _settings.INTERACTIVE_MODE = False
    try:
        conf = _settings.Settings()
        db = os.environ.get("DATABASE__CONNECTION", os.environ.get("DATABASE_CONNECTION", conf.database.connection))
    except RuntimeError:
        db = os.environ.get("DATABASE__CONNECTION", os.environ.get("DATABASE_CONNECTION", None))
        if db is None:
            print(
                "Unable to proceed in auto mode. One of the following environment variables "
                "must be set correctly: 'DATABASE__CONNECTION', 'DATABASE_CONNECTION'!",
                file=sys.stderr
            )
            return 1
        conf = _setup_config(db, False)
    _settings.INTERACTIVE_MODE = True

    # Configure logging as early as feasible
    logging.config.dictConfig(conf.logging.dict())

    # Perform database migrations after the config file has been loaded successfully
    alembic.config.main(argv=["upgrade", "head"])

    # Create the first application if no app currently exists
    database.init(db, conf.database.debug_sql, create_all=False)
    with database.get_new_session() as session:
        apps = len(session.query(models.Application).all())
    if apps == 0:
        initial_username = os.environ.get("INITIAL_APP_USERNAME", None)
        initial_password = os.environ.get("INITIAL_APP_PASSWORD", None)
        if initial_username is None or initial_password is None:
            if os.environ.get("SKIP_INITIALIZATION", None) is None:
                logger.warning(
                    "You need to set the environment variables 'INITIAL_APP_USERNAME' and "
                    "'INITIAL_APP_PASSWORD' in auto mode to create the first authenticated application.",
                )
        else:
            app_args = argparse.Namespace()
            app_args.app = initial_username
            app_args.password = initial_password
            result = add_app(app_args)
            if result != 0:
                return result

    # Ensure the database has the community user
    if os.environ.get("SKIP_INITIALIZATION", None) is None:
        init_args = argparse.Namespace()
        init_args.database = db
        init_args.community_name = os.environ.get('COMMUNITY_NAME', DEFAULT_COMMUNITY_NAME)
        init_args.no_community = False
        init_args.no_migrations = True
        result = init_project(init_args, no_db_init=True, no_hint=True)
        if result != 0:
            return result

    # Run the API server
    settings = _settings.Settings()
    if args.debug_sql:
        settings.database.debug_sql = args.debug_sql
    port = args.port or settings.server.port
    host = args.host or settings.server.host
    app = create_app(settings=settings)
    logging.getLogger("matebot_core").info(f"Server running at host {host} port {port}")
    uvicorn.run(
        app,
        port=port,
        host=host,
        reload=False,
        workers=1,
        log_config=settings.logging.dict(),
        proxy_headers=True,
        root_path=args.root_path
    )


if __name__ == '__main__':
    program_name = sys.argv[0] if not sys.argv[0].endswith("__main__.py") else "matebot_core"
    namespace = get_parser(program_name).parse_args(sys.argv[1:])

    command_functions = {
        "run": run_server,
        "init": init_project,
        "apps": handle_apps,
        "users": handle_users,
        "auto": run_in_auto_mode,
        "systemd": handle_systemd
    }
    exit(command_functions[namespace.command](namespace))
