import asyncio
from logging.config import fileConfig
from sqlalchemy import pool
from sqlalchemy.ext.asyncio import async_engine_from_config
from alembic import context
from src.core.config import settings
from src.core.database import Base

# Import your domain models here
from src.modules.users.models import User, UserBranch, ParentStudentLink
from src.modules.branches.models import Branch
from src.modules.auth.models import SessionAuth, PasswordResetToken
from src.modules.audit.models import ActivityLog
from src.modules.notifications.models import Notification

config = context.config

config.set_main_option("sqlalchemy.url", settings.DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection):
    context.configure(
        connection=connection,
        target_metadata=target_metadata,
    )
    with context.begin_transaction():
        context.run_migrations()


async def run_migrations_online() -> None:
    # asyncpg does NOT support ?sslmode=require in the URL (that's psycopg2 syntax).
    # Strip it and pass ssl=True via connect_args.
    url = config.get_main_option("sqlalchemy.url")
    connect_args = {}
    if url and ("sslmode=require" in url or "neon.tech" in url):
        connect_args["ssl"] = True
        url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
        print(f"DEBUG alembic: SSL=True, URL suffix: {url.split('@')[-1]}")

    from sqlalchemy.ext.asyncio import create_async_engine
    connectable = create_async_engine(
        url,
        poolclass=pool.NullPool,
        connect_args=connect_args,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    asyncio.run(run_migrations_online())
