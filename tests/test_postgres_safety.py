from contextlib import nullcontext
from pathlib import Path
from runpy import run_path
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from alembic.config import Config

from alembic import context
from support_workflow_agent.db import migration_config as local_config
from tests.conftest import pytest_configure
from tests.postgres_support import (
    migration_config,
    postgres_test_url,
    verify_empty_test_database,
    verify_test_connection,
)


@pytest.fixture
def settings() -> dict[str, str]:
    return {
        "TEST_POSTGRES_DB": "support_workflow_test",
        "TEST_POSTGRES_USER": "support_workflow_test",
        "TEST_POSTGRES_PASSWORD": "synthetic:@/%#${literal}",
        "TEST_POSTGRES_HOST": "127.0.0.1",
        "TEST_POSTGRES_PORT": "5433",
    }


def test_test_url_uses_only_explicit_settings(settings: dict[str, str]) -> None:
    settings.update(POSTGRES_DB="support_workflow", POSTGRES_PASSWORD="ignored")
    url = postgres_test_url(settings.get)
    assert url.database == "support_workflow_test"
    assert url.username == "support_workflow_test"
    assert url.drivername == "postgresql+psycopg"
    assert url.host == "127.0.0.1"
    assert url.port == 5433
    assert url.password == settings["TEST_POSTGRES_PASSWORD"]
    assert settings["TEST_POSTGRES_PASSWORD"] not in str(url)
    assert settings["TEST_POSTGRES_PASSWORD"] not in repr(url)
    assert "***" in str(url)


@pytest.mark.parametrize("suffix", ["DB", "USER", "PASSWORD", "HOST", "PORT"])
def test_missing_test_configuration_fails_closed(settings: dict[str, str], suffix: str) -> None:
    settings.pop(f"TEST_POSTGRES_{suffix}")
    settings[f"POSTGRES_{suffix}"] = "must-not-be-used"
    with pytest.raises(ValueError, match="Missing test settings"):
        postgres_test_url(settings.get)


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("TEST_POSTGRES_DB", "support_workflow"),
        ("TEST_POSTGRES_DB", "production_test"),
        ("TEST_POSTGRES_USER", "support_agent"),
        ("TEST_POSTGRES_HOST", "production.example.com"),
        ("TEST_POSTGRES_PORT", "5432"),
        ("PGSERVICE", "production"),
        ("PGSERVICEFILE", "service.conf"),
        ("PGHOSTADDR", "192.0.2.1"),
        ("PGOPTIONS", "-csearch_path=other"),
    ],
)
def test_unsafe_targets_rejected(settings: dict[str, str], key: str, value: str) -> None:
    settings[key] = value
    with pytest.raises(ValueError) as error:
        postgres_test_url(settings.get)
    assert settings["TEST_POSTGRES_PASSWORD"] not in str(error.value)


@pytest.fixture
def verified_connection() -> Mock:
    connection = Mock(spec=sa.Connection)
    connection.execute.return_value.mappings.return_value.one.return_value = {
        "database": "support_workflow_test",
        "role": "support_workflow_test",
        "owner": "support_workflow_test",
        "privileged": False,
        "has_memberships": False,
    }
    return connection


@pytest.mark.parametrize(
    ("key", "value"),
    [
        ("database", "support_workflow"),
        ("role", "support_agent"),
        ("owner", "support_agent"),
        ("privileged", True),
        ("has_memberships", True),
    ],
)
def test_actual_server_identity_must_be_safe(
    verified_connection: Mock, key: str, value: object
) -> None:
    identity = verified_connection.execute.return_value.mappings.return_value.one.return_value
    identity[key] = value
    with pytest.raises(RuntimeError, match="Unsafe test connection"):
        migration_config(verified_connection)


def test_migration_config_keeps_same_verified_connection(verified_connection: Mock) -> None:
    verify_test_connection(verified_connection)
    config = migration_config(verified_connection)
    assert config.attributes["connection"] is verified_connection
    assert config.attributes["configure_logger"] is False


def test_only_allowlisted_environment_keys_are_read(settings: dict[str, str]) -> None:
    allowed = set(settings) | {"PGSERVICE", "PGSERVICEFILE", "PGHOSTADDR", "PGOPTIONS"}

    def read_value(name: str) -> str | None:
        assert name in allowed
        return settings.get(name)

    assert postgres_test_url(read_value).database == "support_workflow_test"


@pytest.mark.parametrize("showlocals", [True, False])
def test_postgres_diagnostics_guard(showlocals: bool) -> None:
    config = Mock(spec=pytest.Config)
    config.getoption.side_effect = {"--run-postgres": True, "showlocals": showlocals}.__getitem__
    if showlocals:
        with pytest.raises(pytest.UsageError, match="protect credentials"):
            pytest_configure(config)
    else:
        pytest_configure(config)


def test_existing_objects_are_never_reset(verified_connection: Mock) -> None:
    verified_connection.scalar.return_value = True
    with pytest.raises(RuntimeError, match="refusing reset"):
        verify_empty_test_database(verified_connection)
    assert verified_connection.scalar.call_count == 1


def test_missing_vector_requires_manual_setup(verified_connection: Mock) -> None:
    verified_connection.scalar.side_effect = [False, False]
    with pytest.raises(RuntimeError, match="administrator install vector"):
        verify_empty_test_database(verified_connection)


def test_empty_database_with_vector_is_accepted(verified_connection: Mock) -> None:
    verified_connection.scalar.side_effect = [False, True]
    verify_empty_test_database(verified_connection)


def test_alembic_supplied_connection_never_loads_dev_configuration(
    monkeypatch: pytest.MonkeyPatch, verified_connection: Mock
) -> None:
    def forbidden(*args, **kwargs):
        pytest.fail("Supplied connection must bypass development config and engine creation")

    config = Config()
    config.attributes["connection"] = verified_connection
    monkeypatch.setattr(context, "config", config, raising=False)
    monkeypatch.setattr(context, "is_offline_mode", lambda: False)
    configure = Mock()
    run = Mock()
    monkeypatch.setattr(context, "configure", configure)
    monkeypatch.setattr(context, "run_migrations", run)
    monkeypatch.setattr(context, "begin_transaction", nullcontext)
    monkeypatch.setattr(local_config, "get_migration_url", forbidden)
    monkeypatch.setattr(sa, "create_engine", forbidden)
    run_path(str(Path(__file__).resolve().parents[1] / "alembic" / "env.py"))
    assert configure.call_args.kwargs["connection"] is verified_connection
    run.assert_called_once_with()
