#!/usr/bin/env python3

import sys
import logging
import argparse

import uvicorn

from matebot_core import settings as _settings
from matebot_core.api.api import create_app


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


if __name__ == '__main__':
    program_name = sys.argv[0] if not sys.argv[0].endswith("__main__.py") else "matebot_core"
    namespace = _get_parser(program_name).parse_args(sys.argv[1:])
    run_server(namespace)
