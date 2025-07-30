"""
Analytics Repository Adapter for Analytics PAL.
This adapter provides a standardized interface to access and manage analytics data sources.
"""

import json
from datetime import datetime
from typing import Any, Dict, List, Optional, Union

import pandas as pd
from pkg.log.logger import Logger

from app.pal.analytics.utils.models import (
    ColumnInfo,
    ColumnStatistics,
    DatabaseInfo,
    SchemaInfo,
    TableInfo,
    TableRelationship,
    ForeignKeyRelationship
)

class AnalyticsRepositoryAdapter:
    """
    Adapter for accessing analytics data sources.
    Provides a unified interface to access different data sources (SQL databases, CSV files, etc.)
    """
    
    def __init__(self, repository, logger=None, redis_client=None, schema_cache_ttl=3600):
        """
        Initialize the analytics repository adapter.
        
        Args:
            repository: The repository instance to adapt
            logger: Optional logger instance
            redis_client: Optional Redis client for caching
            schema_cache_ttl: Time-to-live for schema cache in seconds (default: 1 hour)
        """
        self.repository = repository
        self.logger = logger or Logger()
        self.connection_params = None
        self.redis_client = redis_client
        self.schema_cache_ttl = schema_cache_ttl
        
    @property
    def s3_client(self):
        """
        Provide access to the underlying repository's s3_client.
        
        Returns:
            The s3_client from the repository
        """
        if hasattr(self.repository, 's3_client'):
            return self.repository.s3_client
        return None
        
    def set_connection_params(self, connection_params: Dict[str, Any]):
        """Set connection parameters for the repository"""
        self.connection_params = connection_params
        
    def _get_column_stats(self, column) -> Optional[ColumnStatistics]:
        """Extract column statistics from a column object.
        
        Args:
            column: Column object from repository
            
        Returns:
            ColumnStatistics object or None
        """
        try:
            if not hasattr(column, 'stats') or not column.stats:
                return None
                
            stats = column.stats
            return ColumnStatistics(
                min_value=stats.get('min_value') if isinstance(stats, dict) else None,
                max_value=stats.get('max_value') if isinstance(stats, dict) else None,
                avg_value=stats.get('avg_value') if isinstance(stats, dict) else None,
                median_value=stats.get('median_value') if isinstance(stats, dict) else None,
                null_count=stats.get('null_count') if isinstance(stats, dict) else None,
                distinct_count=stats.get('distinct_count') if isinstance(stats, dict) else None,
                common_values=stats.get('common_values') if isinstance(stats, dict) else None
            )
        except Exception as e:
            self.logger.warning(f"Error extracting column stats: {str(e)}")
            return None
            
    async def get_database_info(self, database_uid: str) -> Optional[DatabaseInfo]:
        """
        Get information about a database by its UID.
        
        Args:
            database_uid: The UID of the database
            
        Returns:
            DatabaseInfo object if found, None otherwise
        """
        self.logger.info(f"Getting database info for: {database_uid}")
        try:
            db = await self.repository.get_database_by_uid(database_uid)
            if not db:
                self.logger.warning(f"Database with UID {database_uid} not found")
                return None
                
            # Extract connection information
            connection_info = {}
            if hasattr(db, 'connection_info'):
                connection_info = db.connection_info
            elif hasattr(db, 'config'):
                connection_info = db.config
                
            # Determine database type
            db_type = "unknown"
            if hasattr(db, 'type'):
                db_type = db.type
            elif hasattr(db, 'db_type'):
                db_type = db.db_type
            elif connection_info and 'type' in connection_info:
                db_type = connection_info['type']
                
            # Get database name
            name = database_uid
            if hasattr(db, 'name'):
                name = db.name
                
            # Get database description
            description = ""
            if hasattr(db, 'description'):
                description = db.description
                
            return DatabaseInfo(
                uid=database_uid,
                name=name,
                description=description,
                type=db_type,
                connection_info=connection_info
            )
        except Exception as e:
            self.logger.error(f"Error getting database info: {str(e)}")
            return None
            
    async def get_database_by_uid(self, database_uid: str) -> Optional[DatabaseInfo]:
        """
        Get database by UID.
        
        Args:
            database_uid: UID of the database
            
        Returns:
            DatabaseInfo object or None if not found
        """
        try:
            db = await self.repository.get_database_by_uid(database_uid)
            if not db:
                self.logger.warning(f"Database with UID {database_uid} not found")
                return None
                
            # Extract connection information
            connection_info = {}
            if hasattr(db, 'connection_info'):
                connection_info = db.connection_info
            elif hasattr(db, 'config'):
                connection_info = db.config
                
            # Determine database type
            db_type = "unknown"
            if hasattr(db, 'type'):
                db_type = db.type
            elif hasattr(db, 'db_type'):
                db_type = db.db_type
            elif connection_info and 'type' in connection_info:
                db_type = connection_info['type']
                
            # Get database name
            name = database_uid
            if hasattr(db, 'name'):
                name = db.name
                
            # Get database description
            description = ""
            if hasattr(db, 'description'):
                description = db.description
                
            return DatabaseInfo(
                uid=database_uid,
                name=name,
                description=description,
                type=db_type,
                connection_info=connection_info
            )
        except Exception as e:
            self.logger.error(f"Error getting database by UID {database_uid}: {str(e)}")
            return None
            
    async def get_tables(self, database_uid: str) -> List[TableInfo]:
        """
        Get a list of tables in a database.
        
        Args:
            database_uid: UID of the database
            
        Returns:
            List of TableInfo objects
        """
        try:
            tables = await self.repository.get_tables_for_database(database_uid)
            result = []
            
            for table in tables:
                table_uid = table.uid if hasattr(table, 'uid') else table.id if hasattr(table, 'id') else None
                if not table_uid:
                    continue
                    
                name = table_uid
                if hasattr(table, 'name'):
                    name = table.name
                    
                description = ""
                if hasattr(table, 'description'):
                    description = table.description
                    
                # Get table schema if available
                schema = None
                if hasattr(table, 'schema'):
                    schema = table.schema
                    
                result.append(TableInfo(
                    uid=table_uid,
                    name=name,
                    description=description,
                    database_uid=database_uid,
                    schema=schema
                ))
                
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting tables for database {database_uid}: {str(e)}")
            return []
            
    async def get_table_by_uid(self, table_uid: str, database_uid: str = None) -> Optional[TableInfo]:
        """
        Get information about a specific table.
        
        Args:
            table_uid: UID of the table
            database_uid: Optional UID of the database (required for some repository implementations)
            
        Returns:
            TableInfo object or None if not found
        """
        try:
            # Check if we need to get database_uid automatically
            if database_uid is None:
                self.logger.info(f"Attempting to find database_uid for table: {table_uid}")
                # Try to find database_uid through repository if possible
                # This is a fallback and may not work with all repositories
                try:
                    table = await self.repository.get_table_by_uid_internal(table_uid)
                    if not table:
                        self.logger.warning(f"Table with UID {table_uid} not found via internal lookup")
                        return None
                except Exception as e:
                    self.logger.error(f"Error getting table info for {table_uid}: {str(e)}")
                    # If we can't get by internal method, we need database_uid
                    self.logger.error("Missing database_uid parameter for get_table_by_uid")
                    return None
            else:
                # Call the repository with both parameters
                self.logger.info(f"Getting table {table_uid} from database {database_uid}")
                try:
                    table = await self.repository.get_table_by_uid(database_uid, table_uid)
                    if not table:
                        self.logger.warning(f"Table with UID {table_uid} not found in database {database_uid}")
                        return None
                except Exception as e:
                    self.logger.error(f"Error getting table info for {table_uid}: {str(e)}")
                    return None
                
            name = table_uid
            if hasattr(table, 'name'):
                name = table.name
                
            description = ""
            if hasattr(table, 'description'):
                description = table.description
                
            database_uid = None
            if hasattr(table, 'database_uid'):
                database_uid = table.database_uid
            elif hasattr(table, 'database_id'):
                database_uid = table.database_id
                
            # Get table schema if available
            schema = None
            if hasattr(table, 'schema'):
                schema = table.schema
                
            return TableInfo(
                uid=table_uid,
                name=name,
                description=description,
                database_uid=database_uid,
                schema=schema
            )
                
        except Exception as e:
            self.logger.error(f"Error getting table info for {table_uid}: {str(e)}")
            return None
            
    async def get_table_by_uid_internal(self, table_uid: str):
        """
        Get the raw table object from the repository.
        This method delegates to the underlying repository's get_table_by_uid_internal method.
        
        Args:
            table_uid: UID of the table
            
        Returns:
            The raw table object from the repository or None if not found
        """
        try:
            if hasattr(self.repository, 'get_table_by_uid_internal'):
                return await self.repository.get_table_by_uid_internal(table_uid)
            else:
                self.logger.error(f"Repository does not support get_table_by_uid_internal method")
                return None
        except Exception as e:
            self.logger.error(f"Error in get_table_by_uid_internal for {table_uid}: {str(e)}")
            return None
            
    async def get_schema(self, database_uid: str, table_uid: Optional[str] = None) -> Optional[SchemaInfo]:
        """
        Get schema information for a database.
        If Redis client is available, tries to get the schema from Redis cache first.
        
        Args:
            database_uid: Database UID
            table_uid: Optional table UID to include only one table
            
        Returns:
            SchemaInfo object or None if error
        """
        # Generate cache key based on parameters
        cache_key = f"schema:{database_uid}"
        if table_uid:
            cache_key += f":{table_uid}"
            
        # Try to get schema from Redis cache if available
        if self.redis_client:
            try:
                self.logger.info(f"Checking Redis cache for schema with key: {cache_key}")
                cached_schema = self.redis_client.get_value(cache_key)
                
                if cached_schema:
                    self.logger.info(f"Schema found in Redis cache")

                    # Convert the dictionary back to SchemaInfo object
                    return SchemaInfo(**cached_schema)
                else:
                    self.logger.info(f"Schema not found in Redis cache, will fetch from database")
            except Exception as e:
                self.logger.error(f"Error accessing Redis cache: {str(e)}")
                # Continue with database fetch if Redis fails
        
        try:
            if not self.repository:
                self.logger.warning("Repository not available for get_schema")
                return None
                
            # Get tables
            self.logger.info(f"Getting tables for database: {database_uid}")
            
            # Handle case when specific table is requested
            if table_uid:
                # Use get_table_by_uid_internal which only needs the table_uid
                table = await self.repository.get_table_by_uid_internal(table_uid)
                if not table:
                    self.logger.warning(f"Table not found: {table_uid}")
                    return None
                    
                tables = [table]
            else:
                # Get all tables
                tables = await self.repository.get_tables_for_database(database_uid)
                
            # Ensure we have tables
            if not tables:
                self.logger.warning(f"No tables found for database: {database_uid}")
                return None
                
            # For each table, get columns and relationships
            enhanced_tables = []
            
            for table in tables:
                try:
                    # Safely get the table id or use name as fallback
                    table_id = table.uid if hasattr(table, 'uid') else table.id if hasattr(table, 'id') else table.name
                    
                    # Get columns
                    try:
                        columns = await self.repository.get_columns_for_table(table_id)
                    except Exception as e:
                        self.logger.error(f"Error getting columns for table {table_id}: {str(e)}")
                        columns = []
                    
                    # Convert to ColumnInfo objects
                    column_infos = []
                    for column in columns:
                        column_infos.append(ColumnInfo(
                            name=column.name,
                            data_type=column.data_type,
                            description=column.description if hasattr(column, 'description') else None,
                            nullable=column.is_nullable if hasattr(column, 'is_nullable') else True,
                            primary_key=column.is_primary_key if hasattr(column, 'is_primary_key') else False,
                            foreign_key=None,  # We'll set this properly if needed
                            statistics=self._get_column_stats(column),
                            semantic_type=None  # Add semantic_type with None as default
                        ))
                    
                    # Create relationships list
                    relationships = []
                    
                    # Create enhanced table info
                    enhanced_table = TableInfo(
                        name=table.name,
                        description=table.description if hasattr(table, 'description') else None,
                        columns=column_infos,
                        relationships=relationships,
                        row_count=table.row_count if hasattr(table, 'row_count') else None,
                        last_updated=table.last_updated if hasattr(table, 'last_updated') else None
                    )
                    
                    enhanced_tables.append(enhanced_table)
                    
                except Exception as e:
                    self.logger.error(f"Error enhancing table {table.name}: {str(e)}")
                
            # Get database info
            db_info = await self.get_database_by_uid(database_uid)
            db_type = db_info.type if db_info else "unknown"
            db_name = db_info.name if db_info else "unknown_database"
            
            # Return schema info
            schema_info = SchemaInfo(
                database_type=db_type,
                database_uid=database_uid,
                database_name=db_name,
                tables=enhanced_tables
            )
            
            # Cache the schema in Redis if Redis client is available
            if self.redis_client:
                try:
                    self.logger.info(f"Caching schema in Redis with key: {cache_key}")

                    # Convert SchemaInfo to dictionary and then to JSON string
                    schema_dict = schema_info.dict()
                    schema_json = json.dumps(schema_dict)
                                        
                    # Store in Redis with TTL
                    self.redis_client.set_value(
                        cache_key, 
                        schema_json,
                        expiry=self.schema_cache_ttl
                    )
                    self.logger.info(f"Schema cached successfully with TTL: {self.schema_cache_ttl}s")
                except Exception as e:
                    self.logger.error(f"Error caching schema in Redis: {str(e)}")
                    # Continue without caching if Redis operation fails
            
            return schema_info
                
        except Exception as e:
            self.logger.error(f"Error getting schema: {str(e)}")
            return None
            
    async def invalidate_schema_cache(self, database_uid: str, table_uid: Optional[str] = None):
        """
        Invalidate the schema cache for a specific database or table.
        
        Args:
            database_uid: Database UID
            table_uid: Optional table UID to invalidate specific table cache
        
        Returns:
            True if successful, False otherwise
        """
        if not self.redis_client:
            self.logger.warning("Redis client not available, cannot invalidate cache")
            return False
            
        try:
            # Generate cache key based on parameters
            if table_uid:
                # Invalidate specific table cache
                cache_key = f"schema:{database_uid}:{table_uid}"
                self.redis_client.delete(cache_key)
                
                # Also invalidate the database-level cache
                db_cache_key = f"schema:{database_uid}"
                self.redis_client.delete(db_cache_key)
            else:
                # Find and delete all keys with this database prefix
                cache_key = f"schema:{database_uid}*"
                keys = self.redis_client.keys(cache_key)
                
                if keys:
                    self.redis_client.delete(*keys)
                    
            self.logger.info(f"Schema cache invalidated for database: {database_uid}")
            return True
        except Exception as e:
            self.logger.error(f"Error invalidating schema cache: {str(e)}")
            return False

    def format_schema_as_string(self, schema: SchemaInfo) -> str:
        """
        Format schema information as a human-readable string.
        
        Args:
            schema: SchemaInfo object
            
        Returns:
            Formatted schema string
        """
        result = [f"Database: {schema.database_name or schema.database_uid} (Type: {schema.database_type})"]
        
        for table in schema.tables:
            result.append(f"\nTable: {table.name}")
            if table.description:
                result.append(f"Description: {table.description}")
                
            # Add columns
            if hasattr(table, 'columns') and table.columns:
                result.append("\nColumns:")
                for col in table.columns:
                    # Build a rich column description with constraints and relationships
                    constraints = []
                    if col.primary_key:
                        constraints.append("PK")
                    if not col.nullable:
                        constraints.append("NOT NULL")
                    if col.unique:
                        constraints.append("UNIQUE")
                    
                    # Include foreign key info
                    fk_info = ""
                    if col.foreign_key:
                        fk_info = f" -> {col.foreign_key.target_table}.{col.foreign_key.target_column}"
                    
                    # Format the constraints
                    constraints_str = f" ({', '.join(constraints)})" if constraints else ""
                    
                    # Final column format
                    col_str = f"- {col.name} ({col.data_type}){constraints_str}{fk_info}"
                    if col.description:
                        col_str += f": {col.description}"
                    result.append(col_str)
            
            # Add relationships
            if hasattr(table, 'relationships') and table.relationships:
                result.append("\nRelationships:")
                for rel in table.relationships:
                    rel_info = f"- {rel.type} to {rel.target_table}"
                    if rel.description:
                        rel_info += f": {rel.description}"
                    result.append(rel_info)
                    
                    # Add column mappings
                    for col_rel in rel.columns:
                        if hasattr(col_rel, 'source_column'):
                            col_info = f"  * {col_rel.source_column} -> {col_rel.target_table}.{col_rel.target_column}"
                            result.append(col_info)
                    
        return "\n".join(result)

    def format_schema_for_query_analysis(self, schema: SchemaInfo) -> str:
        """
        Format schema specifically for query analysis with semantic context.
        
        Args:
            schema: SchemaInfo object
            
        Returns:
            Formatted schema string optimized for query analysis
        """
        result = [f"Database: {schema.database_uid} (Type: {schema.database_type})"]
        
        # Add tables with semantic descriptions
        for table in schema.tables:
            result.append(f"\nTABLE: {table.name}")
            if table.description:
                result.append(f"Description: {table.description}")
            if table.row_count:
                result.append(f"Row count: ~{table.row_count} records")
                
            # Add columns with rich descriptions
            if hasattr(table, 'columns') and table.columns:
                result.append("\nColumns:")
                for col in table.columns:
                    # Build semantic description
                    type_info = col.data_type
                    if hasattr(col, 'semantic_type') and col.semantic_type is not None:
                        type_info += f" ({col.semantic_type})"
                        
                    # Add statistical info if available
                    stats_info = ""
                    if hasattr(col, 'statistics') and col.statistics is not None:
                        stats = []
                        if hasattr(col.statistics, 'unique_count') and col.statistics.unique_count is not None:
                            stats.append(f"{col.statistics.unique_count} unique values")
                        if hasattr(col.statistics, 'null_count') and col.statistics.null_count is not None:
                            stats.append(f"{col.statistics.null_count} null values")
                        if stats:
                            stats_info = f" [{', '.join(stats)}]"
                    
                    col_str = f"- {col.name}: {type_info}{stats_info}"
                    if col.description:
                        col_str += f" - {col.description}"
                    
                    # Add sample values if available
                    if (hasattr(col, 'statistics') and col.statistics is not None and 
                        hasattr(col.statistics, 'sample_values') and col.statistics.sample_values):
                        samples = [str(val) for val in col.statistics.sample_values[:3]]
                        col_str += f" (e.g., {', '.join(samples)})"
                        
                    result.append(col_str)
        
        # Add explicit relationships section
        result.append("\nRELATIONSHIPS BETWEEN TABLES:")
        relationships_added = False
        
        for table in schema.tables:
            if hasattr(table, 'relationships') and table.relationships:
                for rel in table.relationships:
                    relationships_added = True
                    result.append(f"- {table.name} {rel.type} {rel.target_table}")
                    
                    # Add join columns information
                    for col_rel in rel.columns:
                        if hasattr(col_rel, 'source_column'):
                            join_info = f"  * Join on: {table.name}.{col_rel.source_column} = {rel.target_table}.{col_rel.target_column}"
                            result.append(join_info)
        
        if not relationships_added:
            result.append("- No explicit relationships defined")
            
        return "\n".join(result)
        
    def format_schema_for_code_generation(self, schema: SchemaInfo, is_sql: bool = True) -> str:
        """
        Format schema specifically for code generation with technical details.
        
        Args:
            schema: SchemaInfo object
            is_sql: Whether formatting for SQL (True) or Python (False)
            
        Returns:
            Formatted schema string optimized for code generation
        """
        if is_sql:
            # Optimize for SQL generation
            result = [f"-- Database: {schema.database_name or schema.database_uid}"]
            result.append(f"-- Type: {schema.database_type}")
            result.append("")
            
            # Add tables with technical details
            for table in schema.tables:
                result.append(f"-- Table: {table.name}")
                if table.schema != "public":
                    result.append(f"-- Schema: {table.schema}")
                if table.description:
                    result.append(f"-- Description: {table.description}")
                
                # Add CREATE TABLE equivalent
                result.append(f"CREATE TABLE {table.schema}.{table.name} (")
                
                # Add columns with constraints
                column_defs = []
                for col in table.columns:
                    constraints = []
                    if col.primary_key:
                        constraints.append("PRIMARY KEY")
                    if not col.nullable:
                        constraints.append("NOT NULL")
                    if col.unique:
                        constraints.append("UNIQUE")
                    
                    col_def = f"    {col.name} {col.data_type}{' ' + ' '.join(constraints) if constraints else ''}"
                    column_defs.append(col_def)
                
                result.append(",\n".join(column_defs))
                result.append(");")
                result.append("")
                
                # Add foreign key constraints
                for col in table.columns:
                    if col.foreign_key:
                        fk = col.foreign_key
                        result.append(f"-- Foreign Key: {table.name}.{col.name} -> {fk.target_table}.{fk.target_column}")
                        result.append(f"ALTER TABLE {table.schema}.{table.name} ADD CONSTRAINT fk_{table.name}_{col.name} FOREIGN KEY ({col.name}) REFERENCES {table.schema}.{fk.target_table} ({fk.target_column});")
                        result.append("")
            
            # Add common query patterns
            result.append("-- Common JOIN patterns:")
            for table in schema.tables:
                if hasattr(table, 'relationships') and table.relationships:
                    for rel in table.relationships:
                        if rel.columns:
                            col_rel = rel.columns[0]  # Use first column mapping
                            join_clause = f"-- {table.name} JOIN {rel.target_table} ON {table.name}.{col_rel.source_column} = {rel.target_table}.{col_rel.target_column}"
                            result.append(join_clause)
            
            return "\n".join(result)
        else:
            # Optimize for Python/Pandas generation
            result = [f"# Database: {schema.database_name or schema.database_uid}"]
            result.append(f"# Type: {schema.database_type}")
            result.append("")
            
            # For CSV files, provide pandas schema hints
            for table in schema.tables:
                result.append(f"# DataFrame: {table.name}")
                if table.description:
                    result.append(f"# Description: {table.description}")
                
                # Add column information for pandas
                result.append("# Columns:")
                for col in table.columns:
                    dtype = "str"
                    if "int" in col.data_type.lower():
                        dtype = "int64"
                    elif "float" in col.data_type.lower() or "numeric" in col.data_type.lower() or "decimal" in col.data_type.lower():
                        dtype = "float64"
                    elif "bool" in col.data_type.lower():
                        dtype = "bool"
                    elif "date" in col.data_type.lower() or "time" in col.data_type.lower():
                        dtype = "datetime64"
                    
                    result.append(f"#   - {col.name}: {dtype}")
                    if col.description:
                        result.append(f"#     Description: {col.description}")
                
                result.append("")
                
                # Add sample pandas code for common operations
                result.append("# Sample pandas operations:")
                result.append(f"# 1. Basic filtering: df[df['{table.columns[0].name if table.columns else 'column'}'] == value]")
                result.append(f"# 2. Grouping: df.groupby('{table.columns[0].name if table.columns else 'column'}').agg({{'column': 'aggregation'}})")
                if any(col.data_type.lower().startswith(('date', 'time')) for col in table.columns):
                    date_col = next((col.name for col in table.columns if col.data_type.lower().startswith(('date', 'time'))), "date_column")
                    result.append(f"# 3. Time-based analysis: df['{date_col}'] = pd.to_datetime(df['{date_col}'])")
                    result.append(f"#    df.set_index('{date_col}').resample('1D').sum()")
                
                result.append("")
            
            # Add relationship hints for pandas
            result.append("# Relationships (for merging DataFrames):")
            for table in schema.tables:
                if hasattr(table, 'relationships') and table.relationships:
                    for rel in table.relationships:
                        if rel.columns:
                            col_rel = rel.columns[0]  # Use first column mapping
                            merge_hint = f"# df_{table.name}.merge(df_{rel.target_table}, left_on='{col_rel.source_column}', right_on='{col_rel.target_column}')"
                            result.append(merge_hint)
            
            return "\n".join(result)

    def enhance_schema_with_relationships(self, schema: SchemaInfo) -> SchemaInfo:
        """
        Enhance schema with relationship information extracted from foreign keys.
        
        Args:
            schema: SchemaInfo object
            
        Returns:
            Enhanced SchemaInfo with relationships
        """
        # Create a copy to avoid modifying the original
        enhanced_schema = schema.copy(deep=True)
        
        # Set database type and name if not already set
        if not enhanced_schema.database_type and hasattr(enhanced_schema, 'database_uid'):
            db_info = self.get_database_info_sync(enhanced_schema.database_uid)
            if db_info:
                enhanced_schema.database_type = db_info.type
                enhanced_schema.database_name = db_info.name
        
        # Map of table UIDs to names for faster lookup
        table_map = {table.uid: table.name for table in enhanced_schema.tables}
        
        # Detect relationships from foreign keys
        for table in enhanced_schema.tables:
            # Initialize relationships list if not present
            if not hasattr(table, 'relationships') or table.relationships is None:
                table.relationships = []
                
            # Process foreign keys in columns
            for column in table.columns:
                if column.foreign_key:
                    # Get or create foreign key relationship
                    fk = column.foreign_key
                    if isinstance(fk, dict):
                        # Convert legacy dict format to new model
                        target_table = fk.get('table', '')
                        target_column = fk.get('column', '')
                        fk_rel = ForeignKeyRelationship(
                            source_column=column.name,
                            target_table=target_table,
                            target_column=target_column,
                            relationship_type="ONE_TO_MANY"
                        )
                        column.foreign_key = fk_rel
                    else:
                        fk_rel = fk
                    
                    # Add table relationship if not already exists
                    if not any(r.target_table == fk_rel.target_table and r.type == "FOREIGN_KEY" for r in table.relationships):
                        table_rel = TableRelationship(
                            target_table=fk_rel.target_table,
                            type="FOREIGN_KEY",
                            columns=[fk_rel],
                            description=f"Foreign key relationship from {table.name}.{column.name} to {fk_rel.target_table}.{fk_rel.target_column}"
                        )
                        table.relationships.append(table_rel)
                    else:
                        # Add to existing relationship
                        for rel in table.relationships:
                            if rel.target_table == fk_rel.target_table and rel.type == "FOREIGN_KEY":
                                if not any(col.source_column == fk_rel.source_column for col in rel.columns):
                                    rel.columns.append(fk_rel)
        
        # Detect shared column relationships
        table_columns = {}
        for table in enhanced_schema.tables:
            table_columns[table.name] = set(col.name.lower() for col in table.columns)
        
        # Find tables with shared column names (potential joins)
        for table in enhanced_schema.tables:
            for other_table in enhanced_schema.tables:
                if table.name != other_table.name:
                    # Find shared columns
                    shared_cols = table_columns[table.name].intersection(table_columns[other_table.name])
                    if shared_cols:
                        # Skip if a foreign key relationship already exists
                        if any(r.target_table == other_table.name and r.type == "FOREIGN_KEY" for r in table.relationships):
                            continue
                            
                        # Create shared column relationship
                        columns = []
                        for col_name in shared_cols:
                            # Get actual column name with correct case
                            source_col = next((col.name for col in table.columns if col.name.lower() == col_name), col_name)
                            target_col = next((col.name for col in other_table.columns if col.name.lower() == col_name), col_name)
                            
                            columns.append(ForeignKeyRelationship(
                                source_column=source_col,
                                target_table=other_table.name,
                                target_column=target_col
                            ))
                        
                        if columns:
                            table_rel = TableRelationship(
                                target_table=other_table.name,
                                type="SHARED_COLUMN",
                                columns=columns,
                                description=f"Potential join on shared column(s): {', '.join(c.source_column for c in columns)}"
                            )
                            table.relationships.append(table_rel)
        
        self.logger.info("Schema relationships enhancement complete")
        
        return enhanced_schema
    
    def get_database_info_sync(self, database_uid: str) -> Optional[DatabaseInfo]:
        """Synchronous version of get_database_info for internal use"""
        try:
            # Try to get database from repository
            if hasattr(self.repository, 'get_database_by_uid_sync'):
                db = self.repository.get_database_by_uid_sync(database_uid)
            else:
                import asyncio
                db = asyncio.run(self.repository.get_database_by_uid(database_uid))
            
            if not db:
                return None
                
            # Extract connection information
            connection_info = {}
            if hasattr(db, 'connection_info'):
                connection_info = db.connection_info
            elif hasattr(db, 'config'):
                connection_info = db.config
                
            # Determine database type
            db_type = "unknown"
            if hasattr(db, 'type'):
                db_type = db.type
            elif hasattr(db, 'db_type'):
                db_type = db.db_type
            elif connection_info and 'type' in connection_info:
                db_type = connection_info['type']
                
            # Get database name
            name = database_uid
            if hasattr(db, 'name'):
                name = db.name
                
            # Get database description
            description = ""
            if hasattr(db, 'description'):
                description = db.description
                
            return DatabaseInfo(
                uid=database_uid,
                name=name,
                description=description,
                type=db_type,
                connection_info=connection_info
            )
                
        except Exception as e:
            return None

    async def execute_query(self, database_uid: str, query: str) -> pd.DataFrame:
        """
        Execute a SQL query on the specified database.
        
        Args:
            database_uid: The database unique identifier
            query: The SQL query to execute
            
        Returns:
            DataFrame with query results
        """
        self.logger.info(f"AnalyticsRepositoryAdapter.execute_query - Executing query on {database_uid}")
        self.logger.debug(f"AnalyticsRepositoryAdapter.execute_query - Query: {query[:200]}...")
        
        try:
            # Execute query using the repository's 'query' method instead of 'execute_query'
            result = await self.repository.query(database_uid, query)
            
            # Convert to DataFrame
            if result and 'rows' in result and 'columns' in result:
                # Create DataFrame from rows and columns
                df = pd.DataFrame(result['rows'], columns=result['columns'])
                self.logger.info(f"AnalyticsRepositoryAdapter.execute_query - Query executed successfully, returned {len(df)} rows")
                return df
            elif result and isinstance(result, list):
                # Handle case where result is a list of dictionaries
                df = pd.DataFrame(result)
                self.logger.info(f"AnalyticsRepositoryAdapter.execute_query - Query executed successfully, returned {len(df)} rows")
                return df
            elif result and isinstance(result, dict):
                # Handle case where result is a single dictionary
                df = pd.DataFrame([result])
                self.logger.info(f"AnalyticsRepositoryAdapter.execute_query - Query executed successfully, returned 1 row")
                return df
            else:
                # Handle empty or unexpected results
                self.logger.warning(f"AnalyticsRepositoryAdapter.execute_query - Query returned no results or unexpected format")
                return pd.DataFrame()
            
        except Exception as e:
            self.logger.error(f"AnalyticsRepositoryAdapter.execute_query - Error executing query: {str(e)}")
            # Re-raise to let the caller handle the error
            raise

    def _convert_to_schema_info(self, schema_data, db_info=None):
        """Convert database schema data to a structured SchemaInfo object."""
        
        try:
            # Initialize defaults
            database_name = "unknown_database"
            database_type = "unknown"
            database_uid = None
            
            # Extract database info if available
            if db_info:
                database_name = db_info.get('name', database_name)
                database_type = db_info.get('type', database_type)
                database_uid = db_info.get('uid', None)
            
            # Extract from schema_data if it has these fields
            if isinstance(schema_data, dict):
                if 'database_name' in schema_data:
                    database_name = schema_data.get('database_name', database_name)
                if 'database_type' in schema_data:
                    database_type = schema_data.get('database_type', database_type)
                if 'database_uid' in schema_data:
                    database_uid = schema_data.get('database_uid', database_uid)
            
            # Initialize tables list
            tables = []
            
            # Process schema data
            if isinstance(schema_data, dict) and 'tables' in schema_data:
                # Process tables from schema data
                for table_data in schema_data.get('tables', []):
                    # Ensure table has a columns field, even if empty
                    if 'columns' not in table_data:
                        table_data['columns'] = []
                    
                    tables.append(TableInfo(**table_data))
            
            # Create SchemaInfo object with required fields
            schema_info = SchemaInfo(
                database_uid=database_uid or "unknown_database_id",
                database_type=database_type,
                database_name=database_name,
                tables=tables
            )
            
            # Enhance schema with relationships if possible
            return self._enhance_schema_with_relationships(schema_info)
            
        except Exception as e:
            self.logger.error(f"Error converting schema data: {str(e)}")
            # Return minimal valid schema with error information
            return SchemaInfo(
                database_uid="error_database_id",
                database_type="unknown",
                database_name="error_database",
                tables=[],
                description=f"Error processing schema: {str(e)}"
            )

    def _enhance_schema_with_relationships(self, schema: SchemaInfo) -> SchemaInfo:
        """
        Extract and add relationships to the schema based on foreign keys.
        
        Args:
            schema: The schema to enhance with relationships
        """
        try:
            self.logger.info("Enhancing schema with relationships")
            
            # Map of table name to TableInfo for quick lookup
            table_map = {table.name: table for table in schema.tables}
            
            # Extract relationships from foreign keys
            for table in schema.tables:
                for column in table.columns:
                    if column.foreign_key:
                        fk = column.foreign_key
                        # Add relationship to the current table
                        rel = TableRelationship(
                            target_table=fk.table,
                            source_column=column.name,
                            target_column=fk.column,
                            relationship_type="many-to-one",
                            description=f"{table.name}.{column.name} references {fk.table}.{fk.column}"
                        )
                        if table.relationships is None:
                            table.relationships = []
                        table.relationships.append(rel)
                        
                        # Add inverse relationship to the referenced table if it exists
                        if fk.table in table_map:
                            target_table = table_map[fk.table]
                            inverse_rel = TableRelationship(
                                target_table=table.name,
                                source_column=fk.column,
                                target_column=column.name,
                                relationship_type="one-to-many",
                                description=f"{fk.table}.{fk.column} is referenced by {table.name}.{column.name}"
                            )
                            if target_table.relationships is None:
                                target_table.relationships = []
                            target_table.relationships.append(inverse_rel)
            
            # Look for potential relationships based on column names
            for table1 in schema.tables:
                for table2 in schema.tables:
                    if table1.name != table2.name:
                        for col1 in table1.columns:
                            for col2 in table2.columns:
                                # Check for id columns with matching prefixes
                                if (col1.name.endswith('_id') and 
                                    col2.name == 'id' and 
                                    col1.name.startswith(table2.name)):
                                    # Potential relationship found
                                    rel = TableRelationship(
                                        target_table=table2.name,
                                        source_column=col1.name,
                                        target_column=col2.name,
                                        relationship_type="potential",
                                        description=f"Potential relationship: {table1.name}.{col1.name} might reference {table2.name}.{col2.name}"
                                    )
                                    if table1.relationships is None:
                                        table1.relationships = []
                                    
                                    # Check if this relationship isn't already added from foreign keys
                                    existing = False
                                    for existing_rel in table1.relationships:
                                        if (existing_rel.target_table == rel.target_table and 
                                            existing_rel.source_column == rel.source_column and
                                            existing_rel.target_column == rel.target_column):
                                            existing = True
                                            break
                                    
                                    if not existing:
                                        table1.relationships.append(rel)
            
            self.logger.info("Schema relationships enhancement complete")
            
            return schema
            
        except Exception as e:
            self.logger.error(f"Error enhancing schema with relationships: {str(e)}")
            # Don't raise the exception, just log it 

    def _convert_column(self, column) -> ColumnInfo:
        """
        Convert a column object from repository format to ColumnInfo
        
        Args:
            column: Column object from repository
            
        Returns:
            ColumnInfo object
        """
        name = getattr(column, 'name', 'unknown')
        description = getattr(column, 'description', '')
        data_type = getattr(column, 'data_type', 'string')
        is_primary_key = getattr(column, 'is_primary_key', False)
        is_nullable = getattr(column, 'is_nullable', True)
        
        # Try to get statistics if available
        stats = self._get_column_stats(column)
        
        return ColumnInfo(
            name=name,
            description=description, 
            data_type=data_type,
            is_primary_key=is_primary_key,
            is_nullable=is_nullable,
            statistics=stats
        ) 