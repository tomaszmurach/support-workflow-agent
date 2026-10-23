import os
from collections.abc import Iterator

import pytest
from sqlalchemy import Connection, create_engine, pool, text
from sqlalchemy.orm import Session

from alembic import command
from tests.postgres_support import (
    migration_config,
    postgres_test_url,
    verify_empty_test_database,
    verify_test_connection,
)


@pytest.fixture(scope="session")
def pg_database(request: pytest.FixtureRequest) -> Iterator[Connection]:
    __tracebackhide__ = True
    if not request.config.getoption("--run-postgres"):
        pytest.skip("PostgreSQL tests require --run-postgres")
    # Configuration is validated before even creating an engine.
    engine = create_engine(
        postgres_test_url(os.getenv),
        poolclass=pool.NullPool,
        echo=False,
        hide_parameters=True,
        connect_args={
            "connect_timeout": 5,
            "hostaddr": "127.0.0.1",
            "options": "-c search_path=public -c lock_timeout=5000 -c statement_timeout=30000",
        },
    )
    try:
        with engine.connect() as connection:
            transaction = connection.begin()
            try:
                verify_test_connection(connection)
                # Transaction-scoped lock prevents two suites sharing this test DB.
                if not connection.scalar(text("SELECT pg_try_advisory_xact_lock(20260203)")):
                    raise RuntimeError("Another PostgreSQL test run holds the test database lock")
                verify_empty_test_database(connection)
                yield connection
            finally:
                transaction.rollback()
    finally:
        engine.dispose()


@pytest.fixture
def pg_connection(pg_database: Connection) -> Iterator[Connection]:
    # Roll back both Alembic DDL and test rows after each test. Never commit the
    # outer transaction or issue an automatic downgrade as cleanup.
    savepoint = pg_database.begin_nested()
    try:
        command.upgrade(migration_config(pg_database), "head")
        yield pg_database
    finally:
        savepoint.rollback()


@pytest.fixture
def pg_session(pg_connection: Connection) -> Iterator[Session]:
    with Session(pg_connection, join_transaction_mode="create_savepoint") as session:
        yield session
