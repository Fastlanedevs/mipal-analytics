from typing import Dict, List, Any, Optional
import sqlalchemy as sa
from sqlalchemy.engine import Engine
from sqlalchemy import create_engine, MetaData, Table, inspect
import asyncpg

from app.analytics.api.dto import (
    PostgresSchemaDTO,
    PostgresTableDTO,
    PostgresColumnDTO,
    CreatePostgresDatabaseRequestDTO,
    SchemaResponseDTO
)
from app.analytics.repository.schema.schema import get_or_create_database
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.analytics.errors import (
    DatabaseConnectionError,
    DatabaseNotFoundError,
    SchemaValidationError,
    UnauthorizedError
)
from pkg.log.logger import Logger
from pkg.db_util.postgres_conn import PostgresConnection
from app.analytics.entity.analytics import DatabaseType


class PostgresService:
    def __init__(self, analytics_repository: AnalyticsRepository, logger: Logger):
        self.repository = analytics_repository
        self.logger = logger
        self._engines: Dict[str, Engine] = {}

    def _get_engine(self, connection_string: str) -> Engine:
        """Get or create SQLAlchemy engine for the connection string"""
        if connection_string not in self._engines:
            self._engines[connection_string] = create_engine(connection_string)
        return self._engines[connection_string]

    def _get_column_type(self, column: sa.Column) -> str:
        """Map SQLAlchemy column type to our standard type system"""
        type_obj = column.type
        if isinstance(type_obj, sa.String):
            return 'text'
        elif isinstance(type_obj, sa.Integer):
            return 'integer'
        elif isinstance(type_obj, (sa.Float, sa.Numeric)):
            return 'numeric'
        elif isinstance(type_obj, sa.Boolean):
            return 'boolean'
        elif isinstance(type_obj, (sa.DateTime, sa.TIMESTAMP)):
            return 'timestamp'
        elif isinstance(type_obj, sa.Date):
            return 'date'
        elif isinstance(type_obj, sa.Time):
            return 'time'
        elif isinstance(type_obj, sa.JSON):
            return 'json'
        else:
            return 'text'  # Default to text for unknown types

    async def create_database(self, request: CreatePostgresDatabaseRequestDTO):
        """Create/Connect to a PostgreSQL database and map its schema"""
        try:
            # Create database in our system
            database = await get_or_create_database(
                name=request.database_name,
                db_type=DatabaseType.POSTGRES.value,
                description=request.description or f"PostgreSQL database at {request.host}:{request.port}",
                user_id=request.user_id,
                integration_id=request.integration_id
            )

            # Update credentials
            database.update_credentials({
                'host': request.host,
                'port': request.port,
                'user': request.user,
                'password': request.password
            })

            # Map schema - pass both database_name and database_uid to ensure it finds the database
            await self.map_schema(
                database_name=request.database_name,
                database_uid=database.uid,
                user_id=request.user_id
            )

            return database

        except Exception as e:
            self.logger.error(f"Error creating PostgreSQL database: {str(e)}")
            raise DatabaseConnectionError(str(e))

    async def map_schema(self, database_name: Optional[str] = None, database_uid: Optional[str] = None,
                         user_id: str = None) -> SchemaResponseDTO:
        """Maps the schema of a PostgreSQL database
        
        This method connects to a Postgres database, extracts the schema information,
        and stores it in the repository.
        
        Args:
            database_name: The name of the database to map
            database_uid: The UID of the database to map
            user_id: The ID of the user who owns the database
            
        Returns:
            SchemaResponseDTO: The response containing schema information
        """
        try:
            # Get database from repository
            database = None
            if database_uid:
                database = await self.repository.get_database_by_uid(database_uid)
                if database.user_id != user_id:
                    raise UnauthorizedError()
            elif database_name:
                database = await self.repository.get_database(database_name, user_id)

            if not database or database.type != DatabaseType.POSTGRES.value:
                db_id = database_uid or database_name
                raise DatabaseNotFoundError(db_id)

            # Ensure database has a logger for more reliable logging
            if not hasattr(database, 'logger'):
                database.logger = self.logger

            # Get credentials through direct iteration
            credentials = None
            for cred in database.credentials:
                credentials = cred
                break

            if not credentials:
                raise DatabaseConnectionError("No credentials found")

            try:
                conn = await asyncpg.connect(
                    host=credentials.host,
                    port=int(credentials.port),
                    user=credentials.user,
                    password=credentials.password,
                    database=database.name
                )
                try:
                    # Get tables and columns using direct connection
                    tables = await conn.fetch("""
                        SELECT c.table_name, c.column_name, c.data_type, 
                               c.is_nullable, c.column_default,
                               CASE WHEN pk.column_name IS NOT NULL THEN true ELSE false END as is_primary_key
                        FROM information_schema.columns c
                        LEFT JOIN (
                            SELECT kcu.column_name, kcu.table_name
                            FROM information_schema.table_constraints tc
                            JOIN information_schema.key_column_usage kcu 
                                ON tc.constraint_name = kcu.constraint_name
                            WHERE tc.constraint_type = 'PRIMARY KEY'
                            AND tc.table_schema = 'public'
                        ) pk ON c.column_name = pk.column_name AND c.table_name = pk.table_name
                        WHERE c.table_schema = 'public'
                        ORDER BY c.table_name, c.ordinal_position
                    """)

                    # Get foreign key relationships
                    relationships = await conn.fetch("""
                        SELECT 
                            tc.table_name AS foreign_table,
                            kcu.column_name AS foreign_column,
                            ccu.table_name AS referenced_table,
                            ccu.column_name AS referenced_column
                        FROM information_schema.table_constraints AS tc
                        JOIN information_schema.key_column_usage AS kcu 
                            ON tc.constraint_name = kcu.constraint_name
                        JOIN information_schema.constraint_column_usage AS ccu 
                            ON ccu.constraint_name = tc.constraint_name
                        WHERE tc.constraint_type = 'FOREIGN KEY'
                        AND tc.table_schema = 'public'
                    """)
                finally:
                    await conn.close()

                # Group columns by table
                table_columns = {}
                for record in tables:
                    if record['table_name'] not in table_columns:
                        table_columns[record['table_name']] = []
                    table_columns[record['table_name']].append({
                        'name': record['column_name'],
                        'data_type': record['data_type'],
                        'is_nullable': record['is_nullable'] == 'YES',
                        'default': record['column_default'],
                        'is_primary_key': record['is_primary_key']
                    })

                # Store existing tables and their relationships
                existing_tables = {table.name: table for table in database.tables.all()}
                for table in existing_tables.values():
                    table.preserve_relationships()

                # Map schema
                current_tables = set()
                for table_name, columns in table_columns.items():
                    current_tables.add(table_name)


                    # Create or update table - using the database's get_or_create_table method
                    # which now ensures database-specific tables
                    table = database.get_or_create_table(
                        name=table_name,
                        schema='public',
                    )

                    # Add columns
                    current_columns = set()
                    for col in columns:
                        current_columns.add(col['name'])
                        table.get_or_create_column(
                            name=col['name'],
                            data_type=col['data_type'],
                            is_nullable=col['is_nullable'],
                            is_primary_key=col['is_primary_key'],
                            default=col['default']
                        )

                        # Log primary key columns for debugging
                        if col['is_primary_key']:
                            self.logger.info(f"Setting primary key for table {table_name}: {col['name']}")
                            # If this is a primary key column with a name ending in "_id", it might be used for foreign key relationships
                            if col['name'].endswith('_id'):
                                self.logger.info(
                                    f"Primary key column {col['name']} in table {table_name} is a potential foreign key target")

                    # Remove obsolete columns
                    for col in table.columns.all():
                        if col.name not in current_columns:
                            col.delete()

                # Remove obsolete tables - only for this database
                for table_name, table in existing_tables.items():
                    if table_name not in current_tables:
                        table.delete()
                    else:
                        # Restore relationships for remaining tables - only within same database
                        table.restore_relationships(database)

                # After all tables are created, now add the relationships
                relationships_added = 0
                for table_name, table_info in table_columns.items():
                    source_table = database.get_table_by_name(table_name)
                    if not source_table:
                        continue

                    for rel in relationships:
                        target_table_name = rel['referenced_table']
                        target_table = database.get_table_by_name(target_table_name)

                        if not target_table:
                            self.logger.warning(f"Cannot add relationship: target table {target_table_name} not found")
                            continue

                        source_column = rel['foreign_column']
                        target_column = rel['referenced_column']

                        # Check if the source table has the specified column
                        source_column_exists = False
                        for col in source_table.columns.all():
                            if col.name == source_column:
                                source_column_exists = True
                                break

                        if not source_column_exists:
                            self.logger.warning(
                                f"Cannot add relationship: source column {source_table.name}.{source_column} not found")
                            continue

                        # Check if the target table has the specified column
                        target_column_exists = False
                        for col in target_table.columns.all():
                            if col.name == target_column:
                                target_column_exists = True
                                break

                        if not target_column_exists:
                            self.logger.warning(
                                f"Cannot add relationship: target column {target_table_name}.{target_column} not found")
                            continue

                        # Add the relationship
                        try:
                            source_table.add_foreign_key(
                                target_table,
                                source_column,
                                target_column,
                                'ONE_TO_MANY'  # Default to one-to-many for now
                            )

                            # Also add a RELATED_TO relationship for better visualization in Neo4j
                            try:
                                source_table.relates_to.connect(target_table, {'via': source_column})
                                self.logger.info(
                                    f"Added RELATED_TO relationship: {source_table.name} -> {target_table_name} via {source_column}")
                            except Exception as rel_e:
                                self.logger.warning(f"Error adding RELATED_TO relationship: {str(rel_e)}")

                            relationships_added += 1
                            self.logger.info(
                                f"Added relationship: {source_table.name}.{source_column} -> {target_table_name}.{target_column}")
                        except Exception as e:
                            self.logger.warning(
                                f"Error adding relationship {source_table.name}.{source_column} -> {target_table_name}.{target_column}: {e}")

                self.logger.info(f"Added {relationships_added} explicit foreign key relationships from metadata")

                # If no relationships were found in the metadata, try inference
                if relationships_added == 0:
                    self.logger.info(
                        "No explicit foreign key relationships found in database metadata, running enhanced inference...")
                    try:
                        # Log the tables and their columns before running inference
                        self.logger.info(
                            f"[FK Inference] Database schema before inference - {len(table_columns)} tables:")
                        for table_name, columns in table_columns.items():
                            col_names = [col['name'] for col in columns]
                            self.logger.info(
                                f"[FK Inference] Table '{table_name}' with columns: {', '.join(col_names)}")
                            # Log potential primary key candidates
                            pk_cols = [col['name'] for col in columns if col['is_primary_key']]
                            if pk_cols:
                                self.logger.info(
                                    f"[FK Inference] Primary key columns for '{table_name}': {', '.join(pk_cols)}")

                            # Look for potential foreign key columns (ending with _id)
                            fk_cols = [col['name'] for col in columns if
                                       col['name'].endswith('_id') and not col['is_primary_key']]
                            if fk_cols:
                                self.logger.info(
                                    f"[FK Inference] Potential foreign key columns for '{table_name}': {', '.join(fk_cols)}")

                        inferred_count = database.infer_foreign_key_relationships()
                        self.logger.info(
                            f"[FK Inference] Enhanced inference completed: {inferred_count} relationships inferred")

                        # Log the relationships that were inferred
                        if inferred_count > 0:
                            self.logger.info("[FK Inference] Relationship summary:")
                            for table in database.tables.all():
                                for fk_rel in table.foreign_keys.all():
                                    target_table = fk_rel.end_node()
                                    rel_props = fk_rel.properties()
                                    self.logger.info(
                                        f"[FK Inference] {table.name}.{rel_props.get('from_column')} -> {target_table.name}.{rel_props.get('to_column')} ({rel_props.get('type')})")
                    except Exception as e:
                        self.logger.warning(f"[FK Inference] Error during enhanced foreign key inference: {str(e)}")
                else:
                    # Run inference anyway to catch relationships not explicitly defined
                    self.logger.info(
                        f"Running enhanced inference to complement {relationships_added} explicit relationships...")
                    try:
                        # Log existing relationships before running additional inference
                        self.logger.info("[FK Inference] Existing relationships before additional inference:")
                        for table in database.tables.all():
                            for fk_rel in table.foreign_keys.all():
                                try:
                                    # Handle both Neo4j Relationship objects and direct Table objects
                                    try:
                                        # For Neo4j Relationship objects
                                        target_table = fk_rel.end_node()
                                        target_table_name = target_table.name
                                    except (AttributeError, TypeError):
                                        # For direct Table objects or when end_node() is not available
                                        if hasattr(fk_rel, 'name'):
                                            target_table_name = fk_rel.name
                                            target_table = fk_rel
                                        else:
                                            self.logger.warning(
                                                f"[FK Inference] Could not determine target table for relationship from {table.name}")
                                            continue

                                    rel_props = fk_rel.properties()
                                    self.logger.info(
                                        f"[FK Inference] Existing: {table.name}.{rel_props.get('from_column')} -> {target_table_name}.{rel_props.get('to_column')} ({rel_props.get('type')})")
                                except Exception as rel_error:
                                    self.logger.warning(
                                        f"[FK Inference] Error processing relationship for table {table.name}: {str(rel_error)}")
                                    continue

                        inferred_count = database.infer_foreign_key_relationships()
                        self.logger.info(
                            f"[FK Inference] Enhanced inference found {inferred_count} additional relationships")

                        # Log the relationships that were newly inferred
                        if inferred_count > 0:
                            self.logger.info("[FK Inference] New relationship summary:")
                            relationship_count = 0
                            for table in database.tables.all():
                                for fk_rel in table.foreign_keys.all():
                                    try:
                                        relationship_count += 1
                                        # We don't need to log each relationship here, just count them
                                    except Exception as rel_error:
                                        self.logger.warning(
                                            f"[FK Inference] Error counting relationship for table {table.name}: {str(rel_error)}")
                            self.logger.info(
                                f"[FK Inference] Total relationships after inference: {relationship_count}")
                    except Exception as e:
                        self.logger.warning(f"[FK Inference] Error during enhanced foreign key inference: {str(e)}")

                # After inferring foreign key relationships
                try:
                    # Log many-to-many relationships if they exist
                    schema_info = database.get_llm_friendly_schema()
                    many_to_many_relationships = schema_info.get('many_to_many_relationships', [])

                    if many_to_many_relationships:
                        self.logger.info(
                            f"Identified {len(many_to_many_relationships)} many-to-many relationships via junction tables")
                        for rel in many_to_many_relationships:
                            self.logger.info(
                                f"  - {rel['source_table']} <-> {rel['target_table']} via {rel['junction_table']}")
                    else:
                        self.logger.info("No many-to-many relationships identified")

                    # Update the relationship summary to include many-to-many
                    relationships_summary = schema_info.get('relationships_summary', {})
                    relationships_summary['many_to_many_count'] = len(many_to_many_relationships)

                    self.logger.info(
                        f"Schema mapping completed - Mapped {len(tables)} tables, {relationships_added} explicit relationships, {inferred_count} inferred relationships, {len(many_to_many_relationships)} many-to-many relationships")
                except Exception as e:
                    self.logger.warning(f"Error processing many-to-many relationships during schema mapping: {str(e)}")

                return SchemaResponseDTO(
                    message=f"Schema mapped for database {database_name}",
                    tables=[table.name for table in database.tables.all()]
                )

            except Exception as e:
                raise DatabaseConnectionError(str(e))

        except Exception as e:
            self.logger.error(f"Error mapping PostgreSQL schema: {str(e)}")
            if isinstance(e, (DatabaseNotFoundError, DatabaseConnectionError)):
                raise
            raise SchemaValidationError(str(e))

    async def get_table_stats(self, database_name: str, table_name: str, user_id: str) -> Dict[str, Any]:
        """Get statistics for a table"""
        try:
            # Get database
            database = await self.repository.get_database(database_name, user_id)
            if not database or database.type != DatabaseType.POSTGRES.value:
                raise DatabaseNotFoundError(database_name)

            # Get credentials through direct iteration
            credentials = None
            for cred in database.credentials:
                credentials = cred
                break

            if not credentials:
                raise DatabaseConnectionError("No credentials found")

            # Use connection pool if available, otherwise create direct connection
            try:
                # Fallback to direct connection
                conn = await asyncpg.connect(
                    host=credentials.host,
                    port=int(credentials.port),
                    user=credentials.user,
                    password=credentials.password,
                    database=database_name
                )
                try:
                    stats = await conn.fetchrow("""
                        SELECT 
                            pg_stat_get_live_tuples(c.oid) as row_count,
                            pg_size_pretty(pg_total_relation_size(c.oid)) as total_size,
                            pg_size_pretty(pg_table_size(c.oid)) as table_size,
                            pg_size_pretty(pg_indexes_size(c.oid)) as index_size,
                            age(relfrozenxid) as xid_age
                        FROM pg_class c
                        WHERE relname = $1
                    """, table_name)

                    return dict(stats) if stats else {}
                finally:
                    await conn.close()
            except Exception as e:
                raise DatabaseConnectionError(str(e))

        except Exception as e:
            self.logger.error(f"Error getting table statistics: {str(e)}")
            raise

    async def get_table_schema(self, database_name: str, table_name: str, user_id: str) -> Dict[str, Any]:
        """Get schema for a table"""
        try:
            # Get database
            database = await self.repository.get_database(database_name, user_id)
            if not database or database.type != DatabaseType.POSTGRES.value:
                raise DatabaseNotFoundError(database_name)

            # Get credentials through direct iteration
            credentials = None
            for cred in database.credentials:
                credentials = cred
                break

            if not credentials:
                raise DatabaseConnectionError("No credentials found")

            # Connect to database
            try:
                conn = await asyncpg.connect(
                    host=credentials.host,
                    port=int(credentials.port),
                    user=credentials.user,
                    password=credentials.password,
                    database=database_name
                )
            except Exception as e:
                raise DatabaseConnectionError(str(e))

            try:
                # Get table schema
                schema = await conn.fetchrow("""
                    SELECT 
                        pg_get_expr(d.objoid, d.classid) AS expression,
                        a.attname AS column_name,
                        a.attnum AS column_position,
                        a.attnotnull AS is_nullable,
                        a.atttypmod AS data_type
                    FROM pg_attribute a
                    JOIN pg_class c ON a.attrelid = c.oid
                    JOIN pg_namespace n ON c.relnamespace = n.oid
                    JOIN pg_type t ON a.atttypid = t.oid
                    JOIN pg_description d ON c.oid = d.objoid AND a.attnum = ANY(d.objsubid)
                    WHERE c.relname = $1 AND a.attnum > 0 AND NOT a.attisdropped
                    ORDER BY a.attnum
                """, table_name)

                return {
                    'expression': schema['expression'],
                    'column_name': schema['column_name'],
                    'column_position': schema['column_position'],
                    'is_nullable': schema['is_nullable'],
                    'data_type': schema['data_type']
                }

            finally:
                await conn.close()

        except Exception as e:
            self.logger.error(f"Error getting table schema: {str(e)}")
            raise
