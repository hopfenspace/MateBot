#!/usr/bin/env python3

import os
import sys
import getpass
import logging
import argparse

import uvicorn

from matebot_core import settings as _settings
from matebot_core.api.api import create_app


def _handle_systemd() -> int:
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
SyslogIdentifier=matebot

[Install]
WantedBy=multi-user.target
"""

    service_file_path = os.path.join(os.path.abspath("."), "matebot_core.service")
    if os.path.exists(service_file_path):
        print(f"File {service_file_path!r} already exists. Aborting!", file=sys.stderr)
        return 1

    with open(service_file_path, "w") as f:
        f.write(content)

    print(
        f"Successfully created the new file {service_file_path!r}. Now, create a "
        f"symlink from /lib/systemd/system/ to that file. Then use 'systemctl "
        f"daemon-reload' and enable your new service. Check that it works afterwards."
    )

    return 0


def _get_parser(program: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=program,
        description="Run 'uvicorn' ASGI server to serve the MateBot core REST API"
    )

    parser.add_argument(
        "--host",
        type=str,
        metavar="host",
        help="Bind TCP socket to this host (overwrite config)"
    )
    parser.add_argument(
        "--port",
        type=int,
        metavar="port",
        help="Bind TCP socket to this port (overwrite config)"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
    )
    parser.add_argument(
        "--echo",
        action="store_true",
        help="Enable echoing of database actions (overwrite config)"
    )
    parser.add_argument(
        "--reload",
        action="store_true",
        help="Enable auto-reload"
    )
    parser.add_argument(
        "--workers",
        type=int,
        default=None,
        metavar="n",
        help="Number of worker processes (not valid with --reload)",
    )
    parser.add_argument(
        "--access-log",
        action="store_true",
        help="Enable access logs"
    )
    parser.add_argument(
        "--use-colors",
        action="store_true",
        help="Enable colorized output"
    )
    parser.add_argument(
        "--root-path",
        type=str,
        default="",
        metavar="p",
        help="Sub-mount the application below the given path"
    )
    parser.add_argument(
        "--systemd",
        action="store_true",
        help="Configure the systemd service and exit"
    )

    return parser


def run_server(args: argparse.Namespace):
    if args.systemd:
        exit(_handle_systemd())

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


if __name__ == '__main__':
    program_name = sys.argv[0] if not sys.argv[0].endswith("__main__.py") else "matebot_core"
    namespace = _get_parser(program_name).parse_args(sys.argv[1:])
    run_server(namespace)
