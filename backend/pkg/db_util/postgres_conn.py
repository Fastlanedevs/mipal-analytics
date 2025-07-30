from typing import Dict, Optional, Any, List, Tuple, Union, AsyncGenerator
from contextlib import asynccontextmanager
import urllib.parse
import asyncio
from pkg.db_util.types import PostgresConfig
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, AsyncEngine, async_sessionmaker
from sqlalchemy.engine.url import URL
from sqlalchemy.exc import SQLAlchemyError
from pkg.log.logger import Logger


# Assume PostgresConfig, Logger, Base are imported correctly from their respective packages

class PostgresConnection:
    """
    Manages asynchronous PostgresSQL connections using SQLAlchemy, including connection pooling.

    Provides an async session context manager for database operations.
    """

    def __init__(self, db_config: PostgresConfig, logger: Logger):
        self.logger = logger
        self.db_config = db_config
        self._engine: Optional[AsyncEngine] = None
        self._sessionmaker: Optional[async_sessionmaker] = None
        self.logger.info("PostgresConnection initialized.")

    def get_db_url(self) -> str:
        db_name = self.db_config.database
        host = self.db_config.host
        port = self.db_config.port
        username = self.db_config.username
        password = self.db_config.password  # Handle optional password

        # URL encode the password if it exists
        encoded_password = urllib.parse.quote_plus(password) if password else ''

        # Ensure host is provided; fallback isn't handled here, config should be correct
        if not host:
            self.logger.error("Database host is not configured.")
            raise ValueError("Database host configuration is missing.")

        url = f"postgresql+asyncpg://{username}:{encoded_password}@{host}:{port}/{db_name}"
        self.logger.debug(
            f"Generated DB URL (password redacted): postgresql+asyncpg://{username}:***@{host}:{port}/{db_name}")
        return url

    async def get_engine(self) -> AsyncEngine:
        if self._engine is None:
            self.logger.info("Database engine not initialized. Creating new engine...")
            url = self.get_db_url()
            pool_opts = {
                "pool_size": self.db_config.pool_size,
                "max_overflow": self.db_config.max_overflow,
                "pool_timeout": self.db_config.pool_timeout,
                "pool_recycle": self.db_config.pool_recycle,  # Recycle connections e.g., every 30 mins
            }
            self.logger.info(f"Creating async engine with pool options: {pool_opts}")
            try:
                self._engine = create_async_engine(
                    url,
                    echo=False,  # Set to True for debugging SQL
                    # echo_pool="debug", # Set to "debug" for verbose pool logging
                    **pool_opts
                )
                # Optionally, test the connection immediately
                async with self._engine.connect() as conn:
                   self.logger.info("Database connection tested successfully.")


                self._sessionmaker = async_sessionmaker(
                    bind=self._engine,
                    class_=AsyncSession,
                    expire_on_commit=False,
                )
                self.logger.info("Async engine and sessionmaker created successfully.")

            except SQLAlchemyError as e:
                self.logger.error(f"Failed to create SQLAlchemy engine: {e}", exc_info=True)
                raise ConnectionError(f"Could not create database engine: {e}") from e
            except Exception as e:
                self.logger.error(f"An unexpected error occurred during engine creation: {e}", exc_info=True)
                raise ConnectionError(f"Unexpected error creating engine: {e}") from e

        return self._engine

    @asynccontextmanager
    async def get_session(self) -> AsyncGenerator[AsyncSession, None]:
        """Provides an asynchronous SQLAlchemy session with better logging"""
        if self._sessionmaker is None:
            await self.get_engine()
            if self._sessionmaker is None:
                self.logger.error("Sessionmaker is not available even after engine initialization attempt.")
                raise ConnectionError("Database engine/sessionmaker not initialized.")

        session: AsyncSession = self._sessionmaker()
        session_id = id(session)
        # self.logger.debug(f"Acquired session {session_id}.")

        # Log current pool status - helpful for debugging connection issues
        # if self._engine and hasattr(self._engine.pool, "status"):
        #     self.logger.debug(f"Pool status: {self._engine.pool.status()}")

        try:
            yield session
        except SQLAlchemyError as e:
            self.logger.error(f"SQLAlchemy error in session {session_id}: {e}. Rolling back.", exc_info=True)
            await session.rollback()
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in session {session_id}: {e}. Rolling back.", exc_info=True)
            await session.rollback()
            raise
        finally:
            await session.close()
            # self.logger.debug(f"Closed session {session_id}.")

    async def close_engine(self):

        if self._engine:
            self.logger.info("Closing database engine and connection pool...")
            await self._engine.dispose()
            self._engine = None
            self._sessionmaker = None
            self.logger.info("Database engine closed.")
        else:
            self.logger.info("Database engine was not initialized, no need to close.")
