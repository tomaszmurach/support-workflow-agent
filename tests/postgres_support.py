"""Fail-closed configuration and guards for the local integration suite only."""

from collections.abc import Callable
from pathlib import Path

from alembic.config import Config
from sqlalchemy import URL, Connection, text

TEST_DATABASE = "support_workflow_test"
TEST_ROLE = "support_workflow_test"


def postgres_test_url(get_value: Callable[[str], str | None]) -> URL:
    """Read individual settings without retaining an environment/password mapping."""
    __tracebackhide__ = True
    required = ("DB", "USER", "PASSWORD", "HOST", "PORT")
    missing = [f"TEST_POSTGRES_{key}" for key in required if not get_value(f"TEST_POSTGRES_{key}")]
    if missing:
        raise ValueError(f"Missing test settings: {', '.join(missing)}")
    allowed = {"DB": TEST_DATABASE, "USER": TEST_ROLE, "HOST": "127.0.0.1", "PORT": "5433"}
    for key, expected in allowed.items():
        if get_value(f"TEST_POSTGRES_{key}") != expected:
            raise ValueError(f"TEST_POSTGRES_{key} must be {expected}")
    # Do not allow libpq service/routing options to redirect the explicit target.
    if any(get_value(key) for key in ("PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR", "PGOPTIONS")):
        raise ValueError("Unset libpq service/routing overrides before running PostgreSQL tests")
    return URL.create(
        "postgresql+psycopg",
        username=TEST_ROLE,
        password=get_value("TEST_POSTGRES_PASSWORD"),
        host="127.0.0.1",
        port=5433,
        database=TEST_DATABASE,
    )


def verify_test_connection(connection: Connection) -> None:
    """Check the server's actual identity before permitting any migration call."""
    identity = (
        connection.execute(
            text(
                "SELECT current_database() AS database, current_user AS role, "
                "pg_get_userbyid(d.datdba) AS owner, "
                "r.rolsuper OR r.rolcreatedb OR r.rolcreaterole OR r.rolreplication "
                "OR r.rolbypassrls AS privileged, "
                "EXISTS (SELECT 1 FROM pg_auth_members WHERE member = r.oid) AS has_memberships "
                "FROM pg_database d JOIN pg_roles r ON r.rolname = current_user "
                "WHERE d.datname = current_database()"
            )
        )
        .mappings()
        .one()
    )
    if (
        identity["database"] != TEST_DATABASE
        or identity["role"] != TEST_ROLE
        or identity["owner"] != TEST_ROLE
        or identity["privileged"]
        or identity["has_memberships"]
    ):
        raise RuntimeError(
            "Unsafe test connection: require dedicated database and unprivileged owner"
        )


def verify_empty_test_database(connection: Connection) -> None:
    """Refuse existing user relations instead of resetting or deleting them."""
    occupied = connection.scalar(
        text(
            "SELECT EXISTS (SELECT 1 FROM pg_class c JOIN pg_namespace n "
            "ON n.oid = c.relnamespace WHERE n.nspname !~ '^pg_' "
            "AND n.nspname <> 'information_schema' AND c.relkind IN ('r','p','v','m','f','S'))"
        )
    )
    if occupied:
        raise RuntimeError(
            "Test database must have no user tables, views or sequences; refusing reset"
        )
    if not connection.scalar(
        text("SELECT EXISTS (SELECT 1 FROM pg_extension WHERE extname='vector')")
    ):
        raise RuntimeError("Have an administrator install vector in the test database first")


def migration_config(connection: Connection) -> Config:
    """Always pass the verified connection; never let Alembic resolve a dev URL."""
    verify_test_connection(connection)
    config = Config(str(Path(__file__).resolve().parents[1] / "alembic.ini"))
    config.attributes["connection"] = connection
    config.attributes["configure_logger"] = False
    return config
