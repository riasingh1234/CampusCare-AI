"""All SQL lives in this folder. open_repos() gives an endpoint its repositories on ONE database connection.

    with open_repos() as (complaints, reference):
        ...

The connection commits when the block ends normally and rolls back if an error escapes. Tests replace open_repos.
"""
from contextlib import contextmanager

from core.azure_clients import sql_connection

from .complaints import ComplaintsRepository
from .reference import ReferenceRepository


@contextmanager
def open_repos():
    with sql_connection() as conn:
        yield ComplaintsRepository(conn), ReferenceRepository(conn)
