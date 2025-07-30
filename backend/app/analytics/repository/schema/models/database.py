"""
Database model for Neo4j database schema representation.
"""
from typing import Dict, Any, Optional, List
from datetime import datetime
from neomodel import (
    StructuredNode, StringProperty, RelationshipTo, RelationshipFrom,
    ZeroOrMore, One, JSONProperty, BooleanProperty, IntegerProperty, UniqueIdProperty
)
from app.analytics.entity.analytics import DatabaseType
from pkg.log.logger import get_logger

# Initialize logger
logger = get_logger("database_model")


class DatabaseCredential(StructuredNode):
    """Node representing database credentials"""
    host = StringProperty(required=True)
    port = StringProperty(required=True)
    user = StringProperty(required=True)
    password = StringProperty(required=True)  # Encrypted
    created_at = StringProperty(required=True)
    updated_at = StringProperty(required=True)

    # Integration metadata
    integration_id = StringProperty(required=True, unique_index=True)  # Unique integration ID
    user_id = StringProperty(required=True, index=True)  # Owner of the credentials
    is_active = BooleanProperty(default=True)

    # Relationship to database
    database = RelationshipFrom('Database', 'HAS_CREDENTIALS', cardinality=One)

    @staticmethod
    def create_credentials(integration_id: str, host: str, port: int, user: str, password: str, user_id: str,
                           settings: dict = None, metadata: dict = None) -> 'DatabaseCredential':
        """Create new database credentials"""
        now = datetime.utcnow().isoformat()

        # Convert port to string
        port_str = str(port) if port else ""

        return DatabaseCredential(
            integration_id=integration_id,
            host=host,
            port=port_str,
            user=user,
            password=password,  # Should be encrypted
            user_id=user_id,
            created_at=now,
            updated_at=now,
            is_active=True
        ).save()

    def get_password(self) -> str:
        """Get the database password (should be decrypted)"""
        # For now we just return it as is, but this should be decrypted
        return self.password


class DatabaseIntegrationStatus(StructuredNode):
    """Node representing database integration status"""
    status = StringProperty(required=True)  # pending, in_progress, completed, failed
    last_sync = StringProperty()  # ISO format datetime
    error = StringProperty()  # Error message if failed

    def update_status(self, status: str, error: str = None):
        """Update the status of the integration"""
        self.status = status
        self.last_sync = datetime.utcnow().isoformat()
        if error:
            self.error = error
        self.save()

    @staticmethod
    def create_sync_status(integration_id: str, sync_id: str) -> 'DatabaseIntegrationStatus':
        """Create a new sync status node"""
        return DatabaseIntegrationStatus(
            status='pending',
            last_sync=datetime.utcnow().isoformat()
        ).save()


class Database(StructuredNode):
    """Node representing a database (PostgreSQL or CSV)"""
    uid = UniqueIdProperty()  # Add UID
    name = StringProperty(required=True, index=True)  # Name no longer globally unique
    type = StringProperty(required=True, choices={
        DatabaseType.POSTGRES.value: 'PostgreSQL Database',
        DatabaseType.CSV.value: 'CSV Data Source',
        DatabaseType.EXCEL.value: 'Excel Data Source'
    })
    description = StringProperty(default="")

    # Integration metadata
    user_id = StringProperty(required=True, index=True)  # Owner of the database
    unique_key = StringProperty(unique_index=True)  # Compound key: user_id + name
    integration_id = StringProperty(required=True, unique_index=True)  # Unique integration ID
    is_active = BooleanProperty(default=True)
    is_deleted = BooleanProperty(default=False)  # Add is_deleted field
    created_at = StringProperty(required=True)  # ISO format datetime
    updated_at = StringProperty(required=True)  # ISO format datetime

    # Relationships
    tables = RelationshipTo('app.analytics.repository.schema.models.table.Table', 'HAS_TABLE', cardinality=ZeroOrMore)
    credentials = RelationshipTo('DatabaseCredential', 'HAS_CREDENTIALS', cardinality=One)
    sync_status = RelationshipTo('DatabaseIntegrationStatus', 'HAS_SYNC_STATUS', cardinality=ZeroOrMore)

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Ensure logger is always available
        self.logger = logger

        # Create unique key if not provided
        if not kwargs.get('unique_key') and kwargs.get('name') and kwargs.get('user_id'):
            kwargs['unique_key'] = f"{kwargs['user_id']}:{kwargs['name']}"

    def update_credentials(self, credentials: Dict[str, Any]) -> None:
        """Update or create credentials for this database"""
        # Check if credentials exist
        existing_credentials = None
        try:
            # Use direct iteration to get the first credential
            for cred in self.credentials:
                existing_credentials = cred
                break
        except Exception:
            pass

        # Update if credentials exist
        if existing_credentials:
            # Update fields
            if 'host' in credentials:
                existing_credentials.host = credentials['host']
            if 'port' in credentials:
                existing_credentials.port = str(credentials['port'])
            if 'user' in credentials:
                existing_credentials.user = credentials['user']
            if 'password' in credentials:
                existing_credentials.password = credentials['password']  # Should be encrypted

            existing_credentials.updated_at = datetime.utcnow().isoformat()
            existing_credentials.save()

            self.logger.info(f"Updated credentials for database {self.name}")

        else:
            # Create new credentials
            new_credentials = DatabaseCredential.create_credentials(
                integration_id=self.integration_id,
                host=credentials.get('host', ''),
                port=int(credentials.get('port', 0)),
                user=credentials.get('user', ''),
                password=credentials.get('password', ''),  # Should be encrypted
                user_id=self.user_id
            )

            # Connect credentials to database
            try:
                self.credentials.connect(new_credentials)
                self.logger.info(f"Created new credentials for database {self.name}")
            except Exception as e:
                self.logger.error(f"Error connecting credentials to database {self.name}: {str(e)}")
                # Clean up to avoid orphaned credentials
                new_credentials.delete()
                raise

    def get_or_create_sync_status(self) -> DatabaseIntegrationStatus:
        """Get or create a sync status for this database"""
        # Check if sync status exists
        existing_status = None
        try:
            # Use direct iteration to get the latest status
            for status in self.sync_status:
                if not existing_status or (status.last_sync and (
                        not existing_status.last_sync or status.last_sync > existing_status.last_sync)):
                    existing_status = status
        except Exception:
            pass

        # Return if status exists
        if existing_status:
            return existing_status

        # Create new status
        new_status = DatabaseIntegrationStatus(
            status='pending',
            last_sync=datetime.utcnow().isoformat()
        ).save()

        # Connect status to database
        try:
            self.sync_status.connect(new_status)
            self.logger.info(f"Created new sync status for database {self.name}")
            return new_status
        except Exception as e:
            self.logger.error(f"Error connecting sync status to database {self.name}: {str(e)}")
            # Clean up to avoid orphaned status
            new_status.delete()
            raise

    def get_or_create_table(self, name: str, schema: str = 'public', **kwargs):
        """Get or create a table in this database"""
        # Import here to avoid circular imports
        from app.analytics.repository.schema.models.table import Table

        # Check if the table already exists in this database
        table = None
        for t in self.tables.all():
            if t.name == name:
                table = t
                break

        # If found, update properties and return
        if table:
            # Update properties if provided
            updated = False

            if 'description' in kwargs and table.description != kwargs['description']:
                table.description = kwargs['description']
                updated = True

            if 'embedding' in kwargs and table.embedding != kwargs['embedding']:
                table.embedding = kwargs['embedding']
                updated = True

            if 'row_count' in kwargs and table.row_count != kwargs['row_count']:
                table.row_count = kwargs['row_count']
                updated = True

            if 'last_updated' in kwargs and table.last_updated != kwargs['last_updated']:
                table.last_updated = kwargs['last_updated']
                updated = True

            if updated:
                table.save()

            return table

        # Try to find a table with the same name globally - we don't want to use this
        # approach anymore, as we want database-specific tables
        try:
            # Create a unique key for this table in this database
            unique_key = f"{self.uid}:{name}"

            # Create a new table
            table = Table(
                name=name,
                schema=schema,
                database_uid=self.uid,
                unique_key=unique_key,
                full_name=f"{self.name}.{schema}.{name}",
                **kwargs
            ).save()

            # Connect table to this database
            self.tables.connect(table)

            logger.info(f"Created new table {name} in database {self.name}")
            return table

        except Exception as e:
            logger.error(f"Error creating table {name} in database {self.name}: {str(e)}")
            raise

    def add_relationship(self, from_table: str, to_table: str,
                         from_column: str, to_column: str,
                         rel_type: str = 'ONE_TO_MANY'):
        """Add a relationship between two tables in this database"""
        # Find the source table
        source_table = None
        for t in self.tables.all():
            if t.name == from_table:
                source_table = t
                break

        if not source_table:
            raise ValueError(f"Source table '{from_table}' not found in database '{self.name}'")

        # Find the target table
        target_table = None
        for t in self.tables.all():
            if t.name == to_table:
                target_table = t
                break

        if not target_table:
            raise ValueError(f"Target table '{to_table}' not found in database '{self.name}'")

        # Add the relationship
        return source_table.add_foreign_key(
            target_table,
            from_column,
            to_column,
            rel_type
        )

    @property
    def schema_info(self):
        """Get schema information for this database"""
        tables = []
        relationships = []

        # Get all tables
        for table in self.tables.all():
            if table.is_deleted:
                continue

            table_info = {
                'name': table.name,
                'description': table.description,
                'schema': table.schema,
                'row_count': table.row_count,
                'columns': []
            }

            # Get columns for this table
            for column in table.columns.all():
                column_info = {
                    'name': column.name,
                    'data_type': column.data_type,
                    'description': column.description,
                    'is_primary_key': column.is_primary_key,
                    'is_nullable': column.is_nullable,
                    'is_foreign_key': column.is_foreign_key,
                    'default': column.default
                }

                # Add foreign key info if applicable
                if column.is_foreign_key:
                    column_info['references_table'] = column.references_table
                    column_info['references_column'] = column.references_column

                table_info['columns'].append(column_info)

            tables.append(table_info)

            # Get relationships for this table
            for rel in table.foreign_keys.all():
                try:
                    target_table = rel.end_node()
                    props = rel.properties()

                    relationship_info = {
                        'source_table': table.name,
                        'target_table': target_table.name,
                        'from_column': props.get('from_column'),
                        'to_column': props.get('to_column'),
                        'type': props.get('type', 'ONE_TO_MANY')
                    }

                    # Add junction table info if it's a many-to-many relationship
                    if props.get('type') == 'MANY_TO_MANY' and props.get('junction_table'):
                        relationship_info['junction_table'] = props.get('junction_table')
                        relationship_info['junction_source_column'] = props.get('junction_source_column')
                        relationship_info['junction_target_column'] = props.get('junction_target_column')

                    relationships.append(relationship_info)
                except Exception as e:
                    logger.warning(f"Error getting relationship for table {table.name}: {str(e)}")

        return {
            'database_name': self.name,
            'database_type': self.type,
            'tables': tables,
            'relationships': relationships
        }

    def get_llm_friendly_schema(self):
        """Get a human-readable schema for this database suitable for LLM queries"""
        schema_info = self.schema_info

        # Create a simplified schema representation
        tables_info = {}
        for table in schema_info['tables']:
            columns = []
            primary_keys = []
            foreign_keys = []

            for column in table['columns']:
                col_info = f"{column['name']} {column['data_type']}"

                if column['is_primary_key']:
                    col_info += " PRIMARY KEY"
                    primary_keys.append(column['name'])

                if not column['is_nullable']:
                    col_info += " NOT NULL"

                columns.append(col_info)

                if column['is_foreign_key']:
                    fk_info = f"{column['name']} -> {column['references_table']}.{column['references_column']}"
                    foreign_keys.append(fk_info)

            tables_info[table['name']] = {
                'columns': columns,
                'primary_keys': primary_keys,
                'foreign_keys': foreign_keys,
                'row_count': table['row_count'],
                'description': table['description']
            }

        # Process relationships
        relationships = schema_info['relationships']
        relationship_summary = {}
        many_to_many = []

        for rel in relationships:
            source = rel['source_table']
            target = rel['target_table']
            rel_type = rel['type']

            if source not in relationship_summary:
                relationship_summary[source] = []

            summary = f"{source}.{rel['from_column']} -> {target}.{rel['to_column']} ({rel_type})"
            relationship_summary[source].append(summary)

            # Track many-to-many relationships separately
            if rel_type == 'MANY_TO_MANY' and 'junction_table' in rel:
                many_to_many.append({
                    'source_table': source,
                    'target_table': target,
                    'junction_table': rel['junction_table'],
                    'source_column': rel['from_column'],
                    'target_column': rel['to_column'],
                    'junction_source': rel['junction_source_column'],
                    'junction_target': rel['junction_target_column']
                })

        # Generate human-readable schema
        schema_text = f"Database: {self.name} ({self.type})\n\n"

        # Add tables
        schema_text += "Tables:\n"
        for table_name, table_info in tables_info.items():
            schema_text += f"- {table_name}"
            if table_info['description']:
                schema_text += f" ({table_info['description']})"
            schema_text += f" [{table_info['row_count']} rows]\n"

            # Add columns
            schema_text += "  Columns:\n"
            for column in table_info['columns']:
                schema_text += f"    * {column}\n"

            # Add primary keys if not already shown in columns
            if table_info['primary_keys']:
                schema_text += f"  Primary Key(s): {', '.join(table_info['primary_keys'])}\n"

            # Add foreign keys if not already shown in columns
            if table_info['foreign_keys']:
                schema_text += "  Foreign Keys:\n"
                for fk in table_info['foreign_keys']:
                    schema_text += f"    * {fk}\n"

            schema_text += "\n"

        # Add relationships summary
        relationship_count = sum(len(rels) for rels in relationship_summary.values())
        schema_text += f"Relationships ({relationship_count} total):\n"
        for table, rels in relationship_summary.items():
            for rel in rels:
                schema_text += f"- {rel}\n"

        # Summary statistics
        schema_text += f"\nSummary Statistics:\n"
        schema_text += f"- {len(tables_info)} tables\n"
        schema_text += f"- {relationship_count} relationships\n"
        schema_text += f"- {len(many_to_many)} many-to-many relationships\n"

        return {
            'schema_text': schema_text,
            'tables': tables_info,
            'relationships_summary': {
                'total': relationship_count,
                'by_table': relationship_summary
            },
            'many_to_many_relationships': many_to_many
        }

    @classmethod
    def get_or_create(cls, name: str, db_type: str):
        """Get or create a database with the given name and type"""
        try:
            return cls.nodes.get(name=name)
        except cls.DoesNotExist:
            return cls(name=name, type=db_type).save()

    def sync_schema(self, table_data: dict):
        """Sync schema from a dictionary of table data"""
        logger.info(f"Syncing schema for database {self.name}")

        # Get existing tables
        existing_tables = {table.name: table for table in self.tables.all()}

        # Track which tables we've updated
        updated_tables = set()

        # Process each table
        for table_name, table_info in table_data.items():
            updated_tables.add(table_name)

            # Check if table exists
            if table_name in existing_tables:
                table = existing_tables[table_name]
                logger.info(f"Updating existing table {table_name}")
            else:
                # Create new table
                table = self.get_or_create_table(
                    name=table_name,
                    schema=table_info.get('schema', 'public'),
                    description=table_info.get('description', ''),
                    embedding=table_info.get('embedding', []),
                    row_count=table_info.get('row_count', 0),
                    last_updated=datetime.utcnow().isoformat()
                )
                logger.info(f"Created new table {table_name}")

            # Get existing columns
            existing_columns = {col.name: col for col in table.columns.all()}

            # Process columns
            for col_name, col_info in table_info.get('columns', {}).items():
                # Check if column exists
                if col_name in existing_columns:
                    # Update existing column
                    col = existing_columns[col_name]

                    # Update properties
                    updated = False

                    if 'data_type' in col_info and col.data_type != col_info['data_type']:
                        col.data_type = col_info['data_type']
                        updated = True

                    if 'description' in col_info and col.description != col_info['description']:
                        col.description = col_info['description']
                        updated = True

                    if 'is_primary_key' in col_info and col.is_primary_key != col_info['is_primary_key']:
                        col.is_primary_key = col_info['is_primary_key']
                        updated = True

                    if 'is_nullable' in col_info and col.is_nullable != col_info['is_nullable']:
                        col.is_nullable = col_info['is_nullable']
                        updated = True

                    if 'default' in col_info and col.default != col_info['default']:
                        col.default = col_info['default']
                        updated = True

                    if updated:
                        col.save()
                else:
                    # Create new column
                    table.get_or_create_column(
                        name=col_name,
                        data_type=col_info.get('data_type', 'text'),
                        description=col_info.get('description', ''),
                        is_primary_key=col_info.get('is_primary_key', False),
                        is_nullable=col_info.get('is_nullable', True),
                        default=col_info.get('default')
                    )
                    logger.info(f"Created column {col_name} in table {table_name}")

        # Remove tables that no longer exist
        for table_name, table in existing_tables.items():
            if table_name not in updated_tables:
                logger.info(f"Removing table {table_name} that no longer exists")
                table.soft_delete()

        logger.info(f"Schema sync completed for database {self.name}")

        # Update last updated time
        self.updated_at = datetime.utcnow().isoformat()
        self.save()

        return updated_tables

    def get_active_tables(self) -> List['Table']:
        """Get all active (non-deleted) tables"""
        if self.is_deleted:
            return []
        return [t for t in self.tables.all() if not t.is_deleted]

    def get_table_by_name(self, name: str, include_deleted: bool = False) -> Optional['Table']:
        """Get a table by name"""
        if self.is_deleted and not include_deleted:
            return None

        for table in self.tables.all():
            if table.name == name and (include_deleted or not table.is_deleted):
                return table

        return None

    def get_table_by_uid(self, uid: str, include_deleted: bool = False) -> Optional['Table']:
        """Get a table by UID"""
        if self.is_deleted and not include_deleted:
            return None

        for table in self.tables.all():
            if table.uid == uid and (include_deleted or not table.is_deleted):
                return table

        return None

    def get_deleted_tables(self) -> List['Table']:
        """Get all soft-deleted tables"""
        if self.is_deleted:
            return []
        return [t for t in self.tables.all() if t.is_deleted]

    def infer_foreign_key_relationships(self):
        """
        Infer foreign key relationships between tables based on column naming patterns.
        Returns the number of relationships inferred.
        """
        # Import the function to avoid circular imports
        from app.analytics.repository.schema.services.relationship_service import infer_foreign_key_relationships
        return infer_foreign_key_relationships(self)
