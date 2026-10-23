import re
from io import StringIO
from logging import getLogger
from logging.config import fileConfig
from pathlib import Path
from unittest.mock import Mock

import pytest
import sqlalchemy as sa
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateTable

from alembic import command
from support_workflow_agent.db import migration_config
from support_workflow_agent.db.base import Base
from support_workflow_agent.db.models import Customer, Order, Ticket

ROOT = Path(__file__).resolve().parents[1]


def alembic_config(output: StringIO) -> Config:
    config = Config(str(ROOT / "alembic.ini"), output_buffer=output)
    config.attributes["configure_logger"] = False
    return config


@pytest.mark.parametrize("configure_logger", [None, True, False])
def test_alembic_logging_configuration_is_explicit(
    monkeypatch: pytest.MonkeyPatch, configure_logger: bool | None
) -> None:
    config = Config(str(ROOT / "alembic.ini"), output_buffer=StringIO())
    if configure_logger is not None:
        config.attributes["configure_logger"] = configure_logger
    # Observe calls without actually replacing pytest's logging handlers.
    configure = Mock(spec=fileConfig)
    monkeypatch.setattr("logging.config.fileConfig", configure)
    handlers = list(getLogger().handlers)
    command.upgrade(config, "head", sql=True)
    if configure_logger is False:
        configure.assert_not_called()
    else:
        configure.assert_called_once_with(config.config_file_name, disable_existing_loggers=False)
    assert getLogger().handlers == handlers


@pytest.fixture
def offline_sql(monkeypatch: pytest.MonkeyPatch) -> tuple[str, str]:
    def forbidden(*args, **kwargs):
        pytest.fail("Offline migrations must not load credentials or create an engine")

    monkeypatch.setattr(migration_config, "get_migration_url", forbidden)
    monkeypatch.setattr(sa, "create_engine", forbidden)
    upgrade = StringIO()
    downgrade = StringIO()
    command.upgrade(alembic_config(upgrade), "head", sql=True)
    command.downgrade(alembic_config(downgrade), "0001:base", sql=True)
    return upgrade.getvalue(), downgrade.getvalue()


def test_initial_revision_has_one_head_and_no_parent() -> None:
    scripts = ScriptDirectory.from_config(alembic_config(StringIO()))
    assert scripts.get_heads() == ["0001"]
    revisions = list(scripts.walk_revisions())
    assert len(revisions) == 1
    assert revisions[0].down_revision is None
    assert revisions[0].dependencies is None


def test_upgrade_sql_matches_all_model_columns_and_constraints(
    offline_sql: tuple[str, str],
) -> None:
    upgrade, _ = offline_sql
    assert set(Base.metadata.tables) == {"customers", "orders", "tickets"}
    assert re.findall(r"CREATE TABLE (\w+)", upgrade) == [
        "alembic_version",
        "customers",
        "orders",
        "tickets",
    ]
    assert upgrade.count("CREATE EXTENSION IF NOT EXISTS vector;") == 1
    assert upgrade.index("CREATE EXTENSION") < upgrade.index("CREATE TABLE customers")
    assert "CREATE TYPE" not in upgrade
    assert "is_delayed" not in upgrade

    for model in (Customer, Order, Ticket):
        expected = str(CreateTable(model.__table__).compile(dialect=postgresql.dialect()))
        pattern = rf"CREATE TABLE {model.__tablename__} \((.*?)\n\)"
        actual_body = re.search(pattern, upgrade, re.DOTALL).group(1)
        expected_body = re.search(pattern, expected, re.DOTALL).group(1)

        # Compare full column/constraint declarations independently of constraint
        # ordering. Retain duplicates in the lists to catch duplicated CHECKs.
        def declarations(body: str) -> list[str]:
            return sorted(line.strip().rstrip(",") for line in body.splitlines() if line.strip())

        assert declarations(actual_body) == declarations(expected_body)


def test_downgrade_sql_reverses_dependencies_and_keeps_vector(
    offline_sql: tuple[str, str],
) -> None:
    _, downgrade = offline_sql
    application_tables = [
        name for name in re.findall(r"DROP TABLE (\w+)", downgrade) if name != "alembic_version"
    ]
    assert application_tables == ["tickets", "orders", "customers"]
    assert "DROP EXTENSION" not in downgrade
    assert "CASCADE" not in downgrade


@pytest.fixture
def local_env(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> Path:
    for name in (
        "POSTGRES_USER",
        "POSTGRES_PASSWORD",
        "POSTGRES_DB",
        "POSTGRES_HOST",
        "POSTGRES_PORT",
    ):
        monkeypatch.delenv(name, raising=False)
    path = tmp_path / ".env"
    path.write_text(
        "POSTGRES_USER=test_user\nPOSTGRES_PASSWORD='test:@/%#${literal}'\nPOSTGRES_DB=test_db\n",
        encoding="utf-8",
    )
    return path


def test_migration_url_preserves_literal_credentials_and_local_defaults(local_env: Path) -> None:
    url = migration_config.get_migration_url(local_env)
    assert url.drivername == "postgresql+psycopg"
    assert url.username == "test_user"
    assert url.password == "test:@/%#${literal}"
    assert url.database == "test_db"
    assert url.host == "127.0.0.1"
    assert url.port == 5433
    assert url.password not in str(url)


def test_environment_overrides_dotenv(local_env: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    overrides = {
        "POSTGRES_USER": "override_user",
        "POSTGRES_PASSWORD": "override:@/%#${literal}",
        "POSTGRES_DB": "override_db",
        "POSTGRES_HOST": "localhost",
        "POSTGRES_PORT": "5434",
    }
    for name, value in overrides.items():
        monkeypatch.setenv(name, value)
    url = migration_config.get_migration_url(local_env)
    assert url.username == overrides["POSTGRES_USER"]
    assert url.password == overrides["POSTGRES_PASSWORD"]
    assert url.database == overrides["POSTGRES_DB"]
    assert url.host == overrides["POSTGRES_HOST"]
    assert url.port == 5434

    # CI and other callers may supply all settings without a local .env file.
    assert migration_config.get_migration_url(local_env.parent / "missing.env") == url


@pytest.mark.parametrize("port", ["not-a-port", "0", "65536"])
def test_invalid_port_has_safe_error(
    local_env: Path, monkeypatch: pytest.MonkeyPatch, port: str
) -> None:
    monkeypatch.setenv("POSTGRES_PORT", port)
    with pytest.raises(ValueError, match="^POSTGRES_PORT must be an integer between 1 and 65535$"):
        migration_config.get_migration_url(local_env)


@pytest.mark.parametrize("name", ["POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB"])
def test_missing_credentials_have_safe_error(
    local_env: Path, monkeypatch: pytest.MonkeyPatch, name: str
) -> None:
    monkeypatch.setenv(name, "")
    with pytest.raises(ValueError, match=f"^Missing migration configuration: {name}$"):
        migration_config.get_migration_url(local_env)
