from logging.config import fileConfig
from pathlib import Path

from sqlalchemy import Connection, create_engine, pool

from alembic import context
from support_workflow_agent.db import models  # noqa: F401 -- register all ORM tables
from support_workflow_agent.db.base import Base
from support_workflow_agent.db.migration_config import get_migration_url

config = context.config
if config.config_file_name is not None and config.attributes.get("configure_logger", True):
    fileConfig(config.config_file_name, disable_existing_loggers=False)

# Models must be imported before exposing metadata to autogenerate.
target_metadata = Base.metadata
if set(target_metadata.tables) != {"customers", "orders", "tickets"}:
    raise RuntimeError("Unexpected Alembic metadata; expected customers, orders and tickets")


def run_migrations_offline() -> None:
    """Render PostgreSQL SQL without loading credentials or connecting."""
    context.configure(
        dialect_name="postgresql",
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_on_connection(connection: Connection) -> None:
    """Use the caller's transaction when a connection is supplied."""
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run synchronous migrations using local configuration."""
    connection = config.attributes.get("connection")
    if connection is not None:
        run_on_connection(connection)
        return

    env_file = Path(__file__).resolve().parent.parent / ".env"
    engine = create_engine(
        get_migration_url(env_file), poolclass=pool.NullPool, echo=False, hide_parameters=True
    )
    try:
        with engine.connect() as connection:
            run_on_connection(connection)
    finally:
        engine.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
