from collections.abc import Callable

import psycopg

ConnectionFactory = Callable[[str], psycopg.Connection[tuple[object, ...]]]


def default_connection_factory(database_url: str) -> psycopg.Connection[tuple[object, ...]]:
    return psycopg.connect(
        database_url,
        autocommit=True,
        prepare_threshold=None,
    )
