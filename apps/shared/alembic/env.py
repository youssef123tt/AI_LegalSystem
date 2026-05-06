"""
Alembic environment configuration.

HOW THIS FILE WORKS
-------------------
When you run  `alembic upgrade head`  or  `alembic revision --autogenerate`,
Alembic loads this file to know:

1. WHERE to connect (the database URL)
2. WHAT the schema should look like (Base.metadata from our models)

It then compares the metadata to the actual database and generates or
applies migration scripts.
"""

import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

# ---- Import our models so Alembic can see them ----
# This import is CRITICAL.  If you forget it, `--autogenerate` will
# produce empty migrations because Alembic won't know about any tables.
from shared.models import Base

# Alembic Config object — gives access to values in alembic.ini.
config = context.config

# Set up Python logging from the .ini file.
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Tell Alembic what the "target" schema looks like.
# Alembic compares this metadata against the actual DB to find differences.
target_metadata = Base.metadata


def _get_url() -> str:
    """
    Read DATABASE_URL from the environment.
    This overrides whatever is in alembic.ini, which is intentional:
    in Docker, DATABASE_URL is set via docker-compose environment variables.
    """
    return os.getenv(
        "DATABASE_URL",
        config.get_main_option("sqlalchemy.url", ""),
    )


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode — generates SQL without connecting.
    Useful for producing SQL scripts to run manually.
    """
    context.configure(
        url=_get_url(),
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode — connects to the DB and applies changes.
    This is the normal path when you run `alembic upgrade head`.
    """
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = _get_url()

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
