from pathlib import Path

import pytest


def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption(
        "--run-postgres",
        action="store_true",
        default=False,
        help="Enable tests using only the explicitly configured local PostgreSQL test database",
    )


def pytest_configure(config: pytest.Config) -> None:
    if config.getoption("--run-postgres") and config.getoption("showlocals"):
        raise pytest.UsageError("PostgreSQL tests forbid --showlocals/-l to protect credentials")


def pytest_collection_modifyitems(config: pytest.Config, items: list[pytest.Item]) -> None:
    for item in items:
        # Directory-based marking also protects tests whose author forgets the marker.
        if Path(__file__).parent / "integration" in item.path.parents:
            item.add_marker(pytest.mark.postgres)
        if item.get_closest_marker("postgres") and not config.getoption("--run-postgres"):
            item.add_marker(pytest.mark.skip(reason="PostgreSQL tests require --run-postgres"))
