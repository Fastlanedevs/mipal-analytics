import time

from neomodel import config, db
from neo4j.exceptions import ClientError
from neo4j import GraphDatabase, AsyncGraphDatabase
from pkg.db_util.types import DatabaseConfig
from pkg.log.logger import Logger


class Neo4jConnection:
    def __init__(self, db_config: DatabaseConfig, logger: Logger):
        """Initialize Neo4j connection using neomodel"""
        self.logger = logger
        self.db_config = db_config  # Store config for reconnection
        self.connection_url = db_config.connection_url
        self._connected = False  # Track connection state
        self.driver = None  # Initialize driver to None before connecting
        self.async_driver = None  # Initialize async driver to None

        self.logger.info(f"Initializing Neo4j connection to: {db_config.uri}")
        self.uri = "neo4j+s://" + db_config.uri
        self.username = db_config.username
        self.password = db_config.password
        self.max_pool_size = db_config.max_pool_size
        self.max_retries = db_config.max_retries
        self.retry_delay = db_config.retry_delay

        # Attempt connection
        self._connect()

    def _connect(self) -> None:
        """Establish connection to Neo4j using neomodel"""
        # Skip if already connected
        if self._connected:
            return

        retry_count = 0
        max_retries = self.db_config.max_retries
        retry_delay = self.db_config.retry_delay

        while retry_count < max_retries:
            try:
                self.logger.info(f"Attempting to connect to Neo4j at {self.uri} (attempt {retry_count + 1}/{max_retries})")
                
                # Create synchronous driver for neomodel compatibility
                driver = GraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password),
                    max_connection_pool_size=self.max_pool_size,
                )
                self.driver = driver

                # Create async driver for direct async operations
                async_driver = AsyncGraphDatabase.driver(
                    self.uri,
                    auth=(self.username, self.password),
                    max_connection_pool_size=self.max_pool_size,
                )
                self.async_driver = async_driver

                # Configure neomodel with the synchronous driver
                config.DRIVER = driver
                config.DATABASE_URL = self.connection_url
                # Test connection with a simple query
                db.set_connection(driver=driver)
                results, meta = db.cypher_query("RETURN 1")

                self.logger.info("Successfully connected to Neo4j")
                self._connected = True  # Mark as connected

                # If we got here, connection was successful, so break out of retry loop
                break

            except Exception as e:
                self.driver = None  # Clear driver on failure
                self.async_driver = None  # Clear async driver on failure
                retry_count += 1
                self.logger.warning(f"Connection attempt {retry_count} failed: {str(e)}")

                if retry_count >= max_retries:
                    self.logger.error(f"Failed to connect to Neo4j after {max_retries} attempts: {str(e)}")
                    self._connected = False
                    raise

                time.sleep(retry_delay)

    def reconnect(self) -> bool:
        """Force a reconnection attempt
        
        Returns:
            bool: True if reconnection was successful, False otherwise
        """
        self.logger.info("Attempting to reconnect to Neo4j")
        self._connected = False  # Reset connection state
        self.driver = None  # Clear the driver
        self.async_driver = None  # Clear the async driver
        
        try:
            self._connect()
            return self._connected
        except Exception as e:
            self.logger.error(f"Failed to reconnect to Neo4j: {str(e)}")
            return False

    def close(self) -> None:
        """Clear neomodel connection pool"""
        try:
            db.close_connection()
            if self.driver:
                self.driver.close()
            if self.async_driver:
                self.async_driver.close()
            self._connected = False  # Reset connection state
            self.logger.info("Cleared Neo4j connection pool")
        except Exception as e:
            self.logger.error(f"Error clearing Neo4j connection pool: {e!s}")

    def cypher_query(self, query, params=None, transaction=False):
        """
        Execute a cypher query

        Args:
            query: Cypher query to execute
            params: Optional parameters for the query
            transaction: Whether to wrap in a transaction

        Returns:
            Query results
        """
        retry_count = 0
        max_retries = self.db_config.max_retries
        retry_delay = self.db_config.retry_delay

        while retry_count < max_retries:
            try:
                if transaction:
                    with db.transaction:
                        results, meta = db.cypher_query(query, params or {})
                else:
                    results, meta = db.cypher_query(query, params or {})
                return results
            except Exception as e:
                retry_count += 1
                self.logger.warning(f"Query execution attempt {retry_count} failed: {str(e)}")

                # Check for connection errors that might indicate we need to reconnect
                if "Failed to read from defunct connection" in str(e) or "broken pipe" in str(e).lower():
                    self.logger.warning("Connection appears to be broken, attempting to reconnect...")
                    try:
                        self._connected = False  # Reset connection state before reconnecting
                        self._connect()  # Try to reconnect
                    except Exception as reconnect_error:
                        self.logger.error(f"Reconnection failed: {str(reconnect_error)}")

                if retry_count >= max_retries:
                    self.logger.error(f"Error executing query after {max_retries} attempts: {str(e)}")
                    raise

                time.sleep(retry_delay)
