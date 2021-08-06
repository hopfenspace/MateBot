#!/usr/bin/env python3

import sys
import argparse

import uvicorn

from matebot_core.api.api import app


def _get_parser(program: str) -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog=program,
        description="Run 'uvicorn' ASGI server to serve the MateBot core REST API"
    )

    parser.add_argument(
        "--host",
        type=str,
        default="127.0.0.1",
        metavar="host",
        help="Bind TCP socket to this host"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        metavar="port",
        help="Bind TCP socket to this port"
    )
    parser.add_argument(
        "--debug",
        action="store_true",
        help="Enable debug mode"
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

    uvicorn.run(
        app,
        port=args.port,
        host=args.host,
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
