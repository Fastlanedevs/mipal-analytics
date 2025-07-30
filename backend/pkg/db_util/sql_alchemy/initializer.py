from pkg.db_util.sql_alchemy.declarative_base import Base
from pkg.db_util.postgres_conn import PostgresConnection
from sqlalchemy.exc import SQLAlchemyError, IntegrityError
from sqlalchemy import text
from pkg.log.logger import Logger
from typing import Optional, Any, List


class DatabaseInitializer:
    """Handles the initialization of database schema based on SQLAlchemy models."""

    def __init__(self, postgres_conn: PostgresConnection, logger: Logger):
        """
        Initializes the DatabaseInitializer.

        Args:
            postgres_conn: PostgreSQL connection manager.
            logger: An instance of a logger class.
        """
        self.postgres_conn = postgres_conn
        self.db_engine: Optional[Any] = None
        self.logger = logger
        self.logger.info("DatabaseInitializer initialized.")

    async def initialize(self) -> "DatabaseInitializer":
        """Initialize the database engine."""
        self.db_engine = await self.postgres_conn.get_engine()
        return self

    async def install_extensions(self) -> None:
        """
        Install required PostgreSQL extensions.
        """
        if self.db_engine is None:
            await self.initialize()

        extensions: List[str] = [
            "pg_trgm",  # Required for trigram GIN indexes
            "vector",   # Required for pgvector
        ]

        self.logger.info("Installing required PostgreSQL extensions...")
        
        installed_extensions: List[str] = []
        
        try:
            async with self.db_engine.begin() as conn:
                for extension in extensions:
                    try:
                        await conn.execute(text(f"CREATE EXTENSION IF NOT EXISTS {extension}"))
                        installed_extensions.append(extension)
                        self.logger.info(f"Extension '{extension}' installed successfully.")
                    except SQLAlchemyError as e:
                        self.logger.warning(f"Failed to install extension '{extension}': {e}")
                        # Continue with other extensions even if one fails
                        continue
        except SQLAlchemyError as e:
            self.logger.error(f"Error during extension installation: {e}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error during extension installation: {e}", exc_info=True)
            raise
        
        # Update schema configuration based on installed extensions
        self._configure_schema_based_on_extensions(installed_extensions)

    def _configure_schema_based_on_extensions(self, installed_extensions: List[str]) -> None:
        """
        Configure schema features based on successfully installed extensions.
        
        Args:
            installed_extensions: List of successfully installed extension names.
        """
        # Check if pg_trgm is available for trigram indexes
        if "pg_trgm" not in installed_extensions:
            self.logger.warning("pg_trgm extension not available. Disabling trigram indexes.")
            # Import and modify the schema configuration
            try:
                import app.knowledge_base.repository.sql_schema.user_documents as schema_module
                schema_module.ENABLE_TRIGRAM_INDEXES = False
                self.logger.info("Trigram indexes disabled in schema configuration.")
            except ImportError as e:
                self.logger.warning(f"Could not import schema module to disable trigram indexes: {e}")
        
        if "vector" not in installed_extensions:
            self.logger.warning("vector extension not available. Vector operations may not work properly.")
        
        self.logger.info(f"Schema configured based on available extensions: {installed_extensions}")

    async def initialize_tables(self, check_first: bool = True) -> None:
        """
        Create all database tables defined in SQLAlchemy models.
        
        Args:
            check_first: Whether to check if tables exist before creating them.
        """
        # First install required extensions
        await self.install_extensions()
        
        # Ensure all models are imported before creating tables
        try:
            # Import here to avoid circular imports but ensure models are registered
            import app.code_execution.repository.sql_schema
            self.logger.info("Imported SQL schema models.")
        except ImportError as e:
            self.logger.warning(f"Failed to import some models: {e}")

        if self.db_engine is None:
            await self.initialize()
            
        self.logger.info("Attempting to initialize database tables...")
        try:
            async with self.db_engine.begin() as conn:
                self.logger.info(f"Running metadata.create_all (checkfirst={check_first})...")
                await conn.run_sync(Base.metadata.create_all, checkfirst=check_first)
                self.logger.info("Tables initialized successfully (or already exist).")
        except SQLAlchemyError as e:
            self.logger.error(f"Error during table initialization: {e}", exc_info=True)
            # Depending on the error, you might want to raise it or handle differently
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error occurred during table initialization: {e}", exc_info=True)
            raise