#!/usr/bin/env python3

import os
import sys
import json
import getpass
import logging
import argparse

import uvicorn

from matebot_core import settings as _settings
from matebot_core.api.api import create_app
from matebot_core.persistence import database, models


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
ExecStart={python_executable} -m matebot_core
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


def get_parser(program: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog=program)

    commands = parser.add_subparsers(
        description="Available sub-commands: init, run, clear, systemd",
        dest="command",
        required=True,
        metavar="<command>",
        help="the sub-command to be executed"
    )

    parser_init = commands.add_parser(
        "init",
        description="Initialize the project by creating config files and some database models"
    )
    parser_run = commands.add_parser(
        "run",
        description="Run 'uvicorn' ASGI server to serve the MateBot core REST API"
    )
    parser_clear = commands.add_parser(
        "clear",
        description=""  # TODO
    )
    parser_systemd = commands.add_parser(
        "systemd",
        description="Create a systemd unit file to run the MateBot core REST API as system service"
    )

    # TODO: parser_init
    parser_init.add_argument(
        "--database",
        type=str,
        metavar="url",
        help="Database connection URL including scheme and auth"
    )
    init_community = parser_init.add_mutually_exclusive_group()
    init_community.add_argument(
        "--no-community",
        action="store_true",
        help="Don't create the community user if it doesn't exist"
    )
    init_community.add_argument(
        "--community",
        type=str,
        metavar="name",
        help="Optional name of the possibly new community user"
    )
    parser_init.add_argument(
        "--application",
        type=str,
        metavar="name",
        help="Name of a newly created application account"
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
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser_run.add_argument(
        "--echo",
        action="store_true",
        help="Enable echoing of database actions (overwrite config)"
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
        "--access-log",
        action="store_true",
        help="Enable access logs"
    )
    parser_run.add_argument(
        "--use-colors",
        action="store_true",
        help="Enable colorized output"
    )
    parser_run.add_argument(
        "--root-path",
        type=str,
        default="",
        metavar="p",
        help="Sub-mount the application below the given path"
    )

    # TODO: parser_clear

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

    return parser


def run_server(args: argparse.Namespace):
    if args.debug:
        print("Do not start the server this way during production!", file=sys.stderr)

    settings = _settings.Settings()
    if args.echo:
        settings.database.echo = args.echo

    port = args.port
    if port is None:
        port = settings.server.port
    host = args.host
    if host is None:
        host = settings.server.host

    app = create_app(settings=settings)

    logging.getLogger(__name__).info(f"Server at host {host} port {port}")
    uvicorn.run(
        "matebot_core.api:api.app" if args.reload else app,
        port=port,
        host=host,
        debug=args.debug,
        reload=args.reload,
        workers=args.workers,
        log_level="debug" if args.debug else "info",
        access_log=args.access_log,
        use_colors=args.use_colors,
        proxy_headers=True,
        root_path=args.root_path
    )


def init_project(args: argparse.Namespace) -> int:
    settings = _settings.read_settings_from_json_source(False)
    if not settings:
        print("No settings file found. A basic config will be created now interactively.")
        settings = _settings.get_default_config()

        if args.database:
            settings["database"]["connection"] = args.database
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

    config = _settings.config.CoreConfig(**_settings.read_settings_from_json_source(False))
    database.init(config.database.connection, config.database.echo)
    session = database.get_new_session()

    if not args.no_community:
        specials = session.query(models.User).filter_by(special=True).all()
        if len(specials) > 1:
            raise RuntimeError("CRITICAL ERROR. Please drop a bug report.")
        if len(specials) == 0:
            session.add(models.User(
                active=True,
                special=True,
                external=False,
                permission=False,
                name=args.community
            ))
            session.commit()

    if len(session.query(models.Application).all()) == 0:
        name = args.application
        if not name:
            print(
                "\nThere's no registered application yet. Nobody can use the API "
                "without an application account. Skip this step by pressing Enter. "
                "Otherwise type in the name of the new application account below."
            )
            name = input("> ")
        if name:
            session.add(models.Application(name=name))
            session.commit()

    session.flush()
    session.close()

    print("Done.")
    return 0


def clear_project(args: argparse.Namespace) -> int:
    print("This feature is currently not available.", file=sys.stderr)
    return 1


if __name__ == '__main__':
    program_name = sys.argv[0] if not sys.argv[0].endswith("__main__.py") else "matebot_core"
    namespace = get_parser(program_name).parse_args(sys.argv[1:])

    command_functions = {
        "run": run_server,
        "init": init_project,
        "systemd": handle_systemd,
        "clear": clear_project
    }
    exit(command_functions[namespace.command](namespace))
