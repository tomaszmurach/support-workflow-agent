"""Local Alembic connection configuration; requires development dependencies."""

import os
from pathlib import Path

from dotenv import dotenv_values
from sqlalchemy import URL


def get_migration_url(env_file: Path) -> URL:
    """Build a Psycopg URL without interpolating or logging credential values."""
    values = {**dotenv_values(env_file, interpolate=False), **os.environ}
    required = ("POSTGRES_USER", "POSTGRES_PASSWORD", "POSTGRES_DB")
    missing = [name for name in required if not values.get(name)]
    if missing:
        raise ValueError(f"Missing migration configuration: {', '.join(missing)}")
    try:
        port = int(values.get("POSTGRES_PORT", "5433"))
    except (TypeError, ValueError):
        raise ValueError("POSTGRES_PORT must be an integer between 1 and 65535") from None
    if not 1 <= port <= 65535:
        raise ValueError("POSTGRES_PORT must be an integer between 1 and 65535")
    return URL.create(
        "postgresql+psycopg",
        username=values["POSTGRES_USER"],
        password=values["POSTGRES_PASSWORD"],
        host=values.get("POSTGRES_HOST") or "127.0.0.1",
        port=port,
        database=values["POSTGRES_DB"],
    )
