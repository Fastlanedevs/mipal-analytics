"""
SQL Executor for Analytics PAL.
This executor runs SQL queries against PostgreSQL databases.
"""

import pandas as pd
from typing import Tuple, Dict, Any, Optional, List, Union
from pkg.log.logger import Logger

class SQLExecutor:
    """Executes SQL queries against PostgreSQL databases"""
    
    def __init__(self, analytics_repository, logger=None):
        """
        Initialize the SQL executor.
        
        Args:
            analytics_repository: Repository for database access
            logger: Optional logger instance
        """
        self.repository = analytics_repository
        self.logger = logger or Logger()
        
    async def execute(self, query: str, database_uid: str) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Execute a SQL query against a PostgreSQL database.
        
        Args:
            query: The SQL query to execute
            database_uid: UID of the database to query
            
        Returns:
            Tuple containing:
            - DataFrame with query results (or None if error)
            - Error message (or None if successful)
        """
        try:
            self.logger.info(f"Executing SQL query against database {database_uid}")
            self.logger.debug(f"Query: {query}")
            
            # Get database information
            self.logger.info("Getting database information...")
            database = await self.repository.get_database_by_uid(database_uid)
            if not database:
                self.logger.error(f"Database with UID {database_uid} not found")
                return None, f"Database with UID {database_uid} not found"
                
            # Check if it's a Postgres database
            self.logger.info(f"Database type: {database.type}")
            if database.type.lower() != "postgres":
                self.logger.error(f"Database with UID {database_uid} is not a PostgreSQL database")
                return None, f"Database with UID {database_uid} is not a PostgreSQL database"
                
            # Execute the query using the repository
            self.logger.info("Executing query through repository adapter...")
            try:
                result = await self.repository.execute_query(database_uid, query)
                self.logger.info(f"Query executed successfully. Result type: {type(result)}")
                self.logger.debug(f"Result preview: {str(result)[:200]}...")
            except Exception as e:
                self.logger.error(f"Error from repository during query execution: {str(e)}")
                return None, f"Error executing query: {str(e)}"
            
            # Convert to DataFrame
            if isinstance(result, list):
                self.logger.info(f"Converting list result to DataFrame (length: {len(result)})")
                try:
                    df = pd.DataFrame(result)
                    self.logger.info(f"DataFrame created successfully with shape {df.shape}")
                    return df, None
                except Exception as e:
                    self.logger.error(f"Error converting list to DataFrame: {str(e)}")
                    return None, f"Error converting query result to DataFrame: {str(e)}"
            else:
                # Handle other result types (could be a message or other format)
                self.logger.warning(f"Query result is not a list: {type(result)}")
                
                # If it's not a list but has a shape (e.g., already a DataFrame)
                if hasattr(result, 'shape'):
                    self.logger.info(f"Result appears to be a DataFrame with shape {result.shape}")
                    return result, None
                    
                # Try to convert to DataFrame as a last resort
                try:
                    self.logger.info("Attempting to convert non-list result to DataFrame")
                    if result is None:
                        self.logger.warning("Result is None, returning empty DataFrame")
                        return pd.DataFrame(), None
                        
                    df = pd.DataFrame([result] if not isinstance(result, list) else result)
                    self.logger.info(f"Successfully converted to DataFrame with shape {df.shape}")
                    return df, None
                except Exception as e:
                    self.logger.error(f"Failed to convert result to DataFrame: {e}")
                    return None, f"Failed to convert query result to DataFrame: {str(e)}"
                
        except Exception as e:
            self.logger.error(f"Error executing SQL query: {str(e)}")
            
            # Create a helpful error message
            error_msg = str(e)
            if "syntax error" in error_msg.lower():
                error_msg = f"SQL syntax error: {error_msg}"
            elif "permission denied" in error_msg.lower():
                error_msg = f"Permission denied: {error_msg}"
            elif "does not exist" in error_msg.lower():
                error_msg = f"Object does not exist: {error_msg}"
            else:
                error_msg = f"Error executing query: {error_msg}"
                
            return None, error_msg
            
    async def preview_table(self, database_uid: str, table_name: str, limit: int = 10) -> Tuple[Optional[pd.DataFrame], Optional[str]]:
        """
        Get a preview of data from a table
        
        Args:
            database_uid: UID of the database
            table_name: Name of the table to preview
            limit: Maximum number of rows to return
            
        Returns:
            Tuple containing:
            - DataFrame with preview data (or None if error)
            - Error message (or None if successful)
        """
        query = f'SELECT * FROM "{table_name}" LIMIT {limit}'
        return await self.execute(query, database_uid)
        
    async def get_table_schema(self, database_uid: str, table_name: str) -> Tuple[Optional[List[Dict[str, Any]]], Optional[str]]:
        """
        Get schema information for a table
        
        Args:
            database_uid: UID of the database
            table_name: Name of the table
            
        Returns:
            Tuple containing:
            - List of column definitions (or None if error)
            - Error message (or None if successful)
        """
        try:
            # Get all tables for the database
            tables = await self.repository.get_tables(database_uid)
            if not tables:
                return None, f"No tables found in database {database_uid}"
                
            # Find the table with matching name
            table = None
            for t in tables:
                if t.name == table_name:
                    table = t
                    break
                    
            if not table:
                return None, f"Table {table_name} not found in database {database_uid}"
                
            # Return column information
            columns = [
                {
                    "name": col.name,
                    "type": col.data_type,
                    "description": col.description,
                    "is_primary_key": col.is_primary_key,
                    "is_nullable": col.is_nullable
                }
                for col in table.columns
            ]
            
            return columns, None
            
        except Exception as e:
            self.logger.error(f"Error getting table schema: {str(e)}")
            return None, f"Error getting table schema: {str(e)}" 