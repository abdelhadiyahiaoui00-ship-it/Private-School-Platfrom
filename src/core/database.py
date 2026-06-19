import contextlib
import logging
from typing import Annotated, AsyncIterator
from sqlalchemy.ext.asyncio import (
    AsyncConnection,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from fastapi import Depends
from src.core.config import settings

logger = logging.getLogger(settings.APP_NAME)



# Modern SQLAlchemy 2.0 Base — from Version 2
class Base(DeclarativeBase):
    pass


class DatabaseSessionManager:
    def __init__(self, url: str, echo: bool = False) -> None:
        # asyncpg does NOT understand ?sslmode=require (that's psycopg2 syntax).
        # Strip it from the URL and pass ssl=True via connect_args instead.
        connect_args = {}
        if url and ("sslmode=require" in url or "neon.tech" in url):
            connect_args["ssl"] = True
            url = url.replace("?sslmode=require", "").replace("&sslmode=require", "")
            logger.info("DB SSL enabled (sslmode stripped from URL)")

        self._engine = create_async_engine(
            url,
            echo=echo,
            connect_args=connect_args,
            pool_pre_ping=True,
            pool_size=10,
            max_overflow=20,
            pool_recycle=1800,
        )
        self._sessionmaker = async_sessionmaker(
            bind=self._engine,
            autocommit=False,
            autoflush=False,
            expire_on_commit=False,   # from Version 2 — critical
        )

    async def close(self) -> None:
        if self._engine is None:      # null check from Version 1
            raise Exception("DatabaseSessionManager is not initialized")
        await self._engine.dispose()
        self._engine = None
        self._sessionmaker = None

    @contextlib.asynccontextmanager
    async def connect(self) -> AsyncIterator[AsyncConnection]:
        if self._engine is None:      # null check from Version 1
            raise Exception("DatabaseSessionManager is not initialized")
        async with self._engine.begin() as connection:
            try:
                yield connection
            except Exception:
                await connection.rollback()
                raise

    @contextlib.asynccontextmanager
    async def session(self) -> AsyncIterator[AsyncSession]:
        if self._sessionmaker is None:  # null check from Version 1
            raise Exception("DatabaseSessionManager is not initialized")
        session: AsyncSession = self._sessionmaker()
        try:
            yield session
            await session.commit()    # missing from both versions
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


sessionmanager = DatabaseSessionManager(
    url=settings.DATABASE_URL,
    echo=(settings.ENVIRONMENT == "development"),
)


async def get_db() -> AsyncIterator[AsyncSession]:
    async with sessionmanager.session() as session:
        yield session


# Clean annotated type from Version 1
DBSessionDep = Annotated[AsyncSession, Depends(get_db)]
