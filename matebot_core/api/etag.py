"""
ETag helper library for the core REST API
"""

from fastapi import HTTPException, Request, Response


class CacheHit(HTTPException):
    pass


class PreconditionFailed(HTTPException):
    pass


def handle_cache_hit(request: Request, exc: CacheHit):
    return Response("", 304, headers=exc.headers)


def handle_failed_precondition(request: Request, exc: PreconditionFailed):
    return Response("", 412, headers=exc.headers)
