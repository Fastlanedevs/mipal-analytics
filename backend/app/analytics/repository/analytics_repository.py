from typing import List, Any, Optional, Dict, Union
from fastapi import HTTPException, UploadFile
from fastapi.encoders import jsonable_encoder
import json
import time
import asyncio
import numpy as np
import pandas as pd
from datetime import datetime
import uuid
import logging
from app.analytics.repository.storage.s3_client import SchemaS3Client
from neomodel import (
    StructuredNode, StringProperty, RelationshipTo, RelationshipFrom,
    One, ZeroOrMore, DateTimeProperty, IntegerProperty, BooleanProperty, JSONProperty,
    DoesNotExist, db
)
from app.analytics.repository.schema.schema import (
    Database, Table, Column,
    DatabaseCredential, 
    DatabaseIntegrationStatus,
    get_or_create_database
)
from app.analytics.entity.analytics import DatabaseType
from app.analytics.api.dto import (
    DatabaseDTO, TableDTO, ColumnDTO, PostgresDatabaseDTO, CreatePostgresDatabaseRequestDTO,
    CSVDatabaseDTO, CreateCSVDatabaseRequestDTO, PostgresTableDTO
)
from app.middleware.auth import TokenData



class AnalyticsRepository:
    def __init__(self, db=None, logger=None, s3_client: SchemaS3Client = None):
        # Updated to work without Neo4jConnection
        self.db = db  # This will be None but we can use neomodel directly
        self.logger = logger or logging.getLogger(__name__)
        self.s3_client = s3_client

    async def get_schema(self, database_uid: str, table_uid: Optional[str] = None):
        """
        Get schema information for a database or specific table.
        This method is added to support the AnalyticsRepositoryAdapter's get_schema method.
        
        Args:
            database_uid: Database UID
            table_uid: Optional table UID to include only one table
            
        Returns:
            A schema object with consistent structure containing database and table information
        """
        try:
            self.logger.info(f"Getting schema for database: {database_uid}")
            # Get database
            database = await self.get_database_by_uid(database_uid)
            if not database:
                self.logger.warning(f"Database not found: {database_uid}")
                return None
                
            # Add the properties that the adapter expects
            database.database_uid = database.uid
            database.database_type = database.type
            database.database_name = database.name
                
            # If table_uid is provided, get only that specific table
            if table_uid:
                table = database.get_table_by_uid(table_uid)
                if not table:
                    self.logger.warning(f"Table not found: {table_uid}")
                    return None
                
                # Create a schema-like object with a single table
                # This ensures a consistent structure regardless of whether a specific table was requested
                schema_obj = type('SchemaInfo', (), {
                    'database_uid': database.uid,
                    'database_type': database.type,
                    'database_name': database.name,
                    'tables': [table],  # Wrap the table in a list to maintain consistent structure
                    'description': database.description if hasattr(database, 'description') else None
                })
                self.logger.info(f"Schema object: {schema_obj}")
                return schema_obj
                
            # Otherwise return the database info
            return database
        except Exception as e:
            self.logger.error(f"Error getting schema: {str(e)}")
            return None
            
    async def list_databases(self, user_id: str) -> List[DatabaseDTO]:
        """List all mapped databases"""
        try:
            databases = Database.nodes.filter(user_id=user_id)
            return [
                DatabaseDTO(
                    uid=db.uid,
                    name=db.name,
                    type=db.type,
                    description=db.description,
                    user_id=db.user_id,
                    integration_id=db.integration_id,
                    is_active=db.is_active,
                    created_at=db.created_at,
                    updated_at=db.updated_at,
                    tables=[
                        TableDTO(
                            uid=table.uid,
                            name=table.name,
                            schema_name=table.schema,
                            columns=[
                                ColumnDTO(
                                    uid=col.uid,
                                    name=col.name,
                                    data_type=col.data_type,
                                    description=col.description,
                                    is_primary_key=col.is_primary_key,
                                    is_nullable=col.is_nullable,
                                    default=col.default,
                                    stats=col.stats
                                ) for col in table.columns.all()
                            ],
                            description=table.description,
                            row_count=table.row_count,
                            last_updated=table.last_updated
                        ) for table in db.tables.all()
                    ]
                ) for db in databases
            ]
        except Exception as e:
            self.logger.error(f"Error listing databases: {e!s}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_postgres_databases(self) -> List[PostgresDatabaseDTO]:
        """List all PostgreSQL databases"""
        try:
            databases = Database.nodes.filter(type=DatabaseType.POSTGRES.value)
            return [
                PostgresDatabaseDTO(
                    uid=db.uid,
                    name=db.name,
                    type=db.type,
                    description=db.description,
                    user_id=db.user_id,
                    integration_id=db.integration_id,
                    is_active=db.is_active,
                    created_at=db.created_at,
                    updated_at=db.updated_at,
                    host=db.credentials.single()['host'],
                    port=int(db.credentials.single()['port']),
                    user=db.credentials.single()['user'],
                    tables=[
                        PostgresTableDTO(
                            uid=table.uid,
                            name=table.name,
                            schema_name=table.schema,
                            columns=[
                                PostgresColumnDTO(
                                    uid=col.uid,
                                    name=col.name,
                                    data_type=col.data_type,
                                    description=col.description,
                                    is_primary_key=col.is_primary_key,
                                    is_nullable=col.is_nullable,
                                    default=col.default,
                                    stats=col.stats,
                                    character_length=None,
                                    numeric_precision=None,
                                    numeric_scale=None,
                                    is_foreign_key=False,
                                    references=None
                                ) for col in table.columns.all()
                            ],
                            description=table.description,
                            row_count=table.row_count,
                            last_updated=table.last_updated,
                            total_size=None,
                            table_size=None,
                            index_size=None,
                            row_estimate=None,
                            has_indices=False,
                            primary_key=None,
                            foreign_keys=[]
                        ) for table in db.tables.all()
                    ]
                ) for db in databases
            ]
        except Exception as e:
            self.logger.error(f"Error listing PostgreSQL databases: {e!s}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_postgres_database(self, request: CreatePostgresDatabaseRequestDTO) -> PostgresDatabaseDTO:
        """Create/Connect to a PostgreSQL database and map its schema"""
        try:
            # Check if database already exists
            try:
                database = Database.nodes.get(name=request.database_name, user_id=request.user_id)
                
                # If database exists, check if it's a PostgreSQL database
                if database.type != DatabaseType.POSTGRES.value:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Database '{request.database_name}' exists but is not a PostgreSQL database"
                    )
                
                # Update credentials
                database.update_credentials({
                    'host': request.host,
                    'port': request.port,
                    'user': request.user,
                    'password': request.password
                })
                
                # Update description if provided
                if request.description:
                    database.description = request.description
                    database.save()
                
                return database
                
            except Database.DoesNotExist:
                conn = psycopg2.connect(
                    dbname=request.database_name,
                    user=request.user,
                    password=request.password,
                    host=request.host,
                    port=request.port
                )
                conn.close()
                
                now = datetime.utcnow().isoformat()
                database = Database(
                    name=request.database_name,
                    type=DatabaseType.POSTGRES.value,
                    user_id=request.user_id,
                    description=request.description or "",
                    integration_id=request.integration_id,
                    created_at=now,
                    updated_at=now,
                    is_active=True,
                    is_deleted=False
                ).save()
                
                # Create and connect credentials
                credentials = DatabaseCredential.create_credentials(
                    integration_id=database.integration_id,
                    host=request.host,
                    port=request.port,
                    user=request.user,
                    password=request.password,
                    user_id=request.user_id
                )
                
                database.credentials.connect(credentials)
                database.save()
                
                sync_status = DatabaseIntegrationStatus.create_sync_status(
                    integration_id=database.integration_id,
                    sync_id=str(uuid.uuid4())
                )
                
                database.sync_status.connect(sync_status)
                database.save()
                
                try:
                    sync_status.update_status('in_progress')
                    await self.map_postgres_schema(connection_details={
                        'host': request.host,
                        'port': request.port,
                        'user': request.user,
                        'password': request.password,
                        'dbname': request.database_name
                    })
                    sync_status.update_status('completed')
                except Exception as e:
                    sync_status.update_status('failed', str(e))
                    raise
                
                return database
                
        except Exception as e:
            self.logger.error(f"Error creating PostgreSQL database: {e!s}")
            raise HTTPException(status_code=500, detail=str(e))

    async def map_postgres_schema(self, connection_details, skip_inference=False):
        """
        Map PostgreSQL schema to Neo4j graph database.
        This function connects to PostgreSQL, retrieves table and column information,
        and syncs the schema into Neo4j while preserving explicitly defined foreign key relationships.

        Args:
            connection_details (dict): PostgreSQL connection details including:
                - host: PostgreSQL host address
                - port: PostgreSQL port
                - database: Database name
                - user: Username
                - password: Password
                - sslmode: SSL mode (optional)
            skip_inference (bool): Skip the inference of foreign key relationships
                                  Set to True to preserve only explicitly defined foreign keys
        
        Returns:
            DatabaseSchema: Database schema object
        """
        try:
            import psycopg2
            from psycopg2 import sql
            from psycopg2.extras import RealDictCursor
            import ssl
            
            # Connect to PostgreSQL
            self.logger.info(f"Connecting to PostgreSQL at {connection_details['host']}:{connection_details['port']}...")
            
            # Set SSL mode to require if present in connection details
            ssl_mode = connection_details.get('sslmode')
            if ssl_mode == 'require':
                # Create SSL context
                ssl_context = ssl.create_default_context()
                ssl_context.check_hostname = False
                ssl_context.verify_mode = ssl.CERT_NONE
                
                # Pass SSL context to connection
                conn = psycopg2.connect(
                    host=connection_details['host'],
                    port=connection_details['port'],
                    dbname=connection_details['database'],
                    user=connection_details['user'],
                    password=connection_details['password'],
                    sslmode='require',
                    sslcontext=ssl_context,
                    cursor_factory=RealDictCursor
                )
            else:
                # Connect without SSL
                conn = psycopg2.connect(
                    host=connection_details['host'],
                    port=connection_details['port'],
                    dbname=connection_details['database'],
                    user=connection_details['user'],
                    password=connection_details['password'],
                    cursor_factory=RealDictCursor
                )
            
            cursor = conn.cursor()
            
            # Create schema dictionary
            db_schema = {
                'name': connection_details['database'],
                'tables': []
            }
            
            # Get all tables
            query = """
            SELECT 
                table_schema, 
                table_name, 
                table_type
            FROM 
                information_schema.tables
            WHERE 
                table_schema NOT IN ('pg_catalog', 'information_schema')
                AND table_type = 'BASE TABLE'
            ORDER BY 
                table_schema, 
                table_name;
            """
            
            cursor.execute(query)
            tables = cursor.fetchall()
            
            self.logger.info(f"Found {len(tables)} tables in database {connection_details['database']}")
            
            # Create a dictionary to map table keys to table objects
            table_dict = {}
            
            # Process each table
            for table in tables:
                table_schema = table['table_schema']
                table_name = table['table_name']
                
                # Get columns for this table
                columns_query = """
                SELECT 
                    column_name, 
                    data_type, 
                    is_nullable,
                    column_default,
                    ordinal_position
                FROM 
                    information_schema.columns
                WHERE 
                    table_schema = %s
                    AND table_name = %s
                ORDER BY 
                    ordinal_position;
                """
                
                cursor.execute(columns_query, (table_schema, table_name))
                columns = cursor.fetchall()
                
                # Get primary key columns
                pk_query = """
                SELECT 
                    c.column_name
                FROM 
                    information_schema.table_constraints tc
                JOIN 
                    information_schema.constraint_column_usage AS ccu USING (constraint_schema, constraint_name)
                JOIN 
                    information_schema.columns AS c ON c.table_schema = tc.constraint_schema
                    AND c.table_name = tc.table_name 
                    AND c.column_name = ccu.column_name
                WHERE 
                    constraint_type = 'PRIMARY KEY'
                    AND tc.table_schema = %s
                    AND tc.table_name = %s;
                """
                
                cursor.execute(pk_query, (table_schema, table_name))
                primary_keys = [pk['column_name'] for pk in cursor.fetchall()]
                
                # Create table object
                table_obj = {
                    'name': table_name,
                    'schema': table_schema,
                    'columns': [],
                    'primary_keys': primary_keys
                }
                
                # Process columns
                for column in columns:
                    column_obj = {
                        'name': column['column_name'],
                        'data_type': column['data_type'],
                        'is_nullable': column['is_nullable'] == 'YES',
                        'default': column['column_default'],
                        'is_primary_key': column['column_name'] in primary_keys,
                        'is_foreign_key': False,
                        'references_table': None,
                        'references_column': None,
                        'references_schema': None
                    }
                    
                    table_obj['columns'].append(column_obj)
                
                # Add table to schema
                db_schema['tables'].append(table_obj)
                
                # Add to table dictionary for easy lookup
                table_dict[f"{table_schema}.{table_name}"] = table_obj
            
            # Get foreign key relationships
            fk_query = """
            SELECT 
                tc.constraint_name, 
                tc.table_schema, 
                tc.table_name, 
                kcu.column_name, 
                ccu.table_schema AS foreign_table_schema,
                ccu.table_name AS foreign_table_name,
                ccu.column_name AS foreign_column_name 
            FROM 
                information_schema.table_constraints AS tc 
            JOIN 
                information_schema.key_column_usage AS kcu ON tc.constraint_name = kcu.constraint_name
                AND tc.table_schema = kcu.table_schema
            JOIN 
                information_schema.constraint_column_usage AS ccu ON ccu.constraint_name = tc.constraint_name
                AND ccu.table_schema = tc.table_schema
            WHERE 
                tc.constraint_type = 'FOREIGN KEY';
            """
            
            cursor.execute(fk_query)
            foreign_keys = cursor.fetchall()
            
            # Add foreign keys to tables
            self.logger.info(f"Found {len(foreign_keys)} explicit foreign key constraints")
            for fk in foreign_keys:
                source_table_key = f"{fk['table_schema']}.{fk['table_name']}"
                target_table_key = f"{fk['foreign_table_schema']}.{fk['foreign_table_name']}"
                
                if source_table_key in table_dict and target_table_key in table_dict:
                    source_table = table_dict[source_table_key]
                    # Find the source column
                    for column in source_table['columns']:
                        if column['name'] == fk['column_name']:
                            # Add foreign key info
                            column['is_foreign_key'] = True
                            column['references_table'] = fk['foreign_table_name']
                            column['references_column'] = fk['foreign_column_name']
                            column['references_schema'] = fk['foreign_table_schema']
                            
                            self.logger.info(f"Found explicit FK: {fk['table_schema']}.{fk['table_name']}.{fk['column_name']} -> "
                                        f"{fk['foreign_table_schema']}.{fk['foreign_table_name']}.{fk['foreign_column_name']}")
                            break
            
            # Close database connection
            cursor.close()
            conn.close()
            
            # Sync the schema to neo4j
            self.logger.info("Syncing schema to Neo4j...")
            database = self.sync_schema(db_schema)
            
            # Infer foreign keys if not explicitly defined and not skipped
            if not skip_inference:
                self.logger.info("\nInferring foreign key relationships from naming patterns...")
                inferred_count = database.infer_foreign_key_relationships()
                self.logger.info(f"Successfully inferred {inferred_count} foreign key relationships")
            else:
                self.logger.info("\nSkipping foreign key inference as requested")
            
            return database
            
        except Exception as e:
            self.logger.error(f"Error mapping PostgreSQL schema: {str(e)}")
            traceback.print_exc()
            raise e

    # Testing helper methods
    def _create_test_data(self, database):
        """Create test data for a database"""
        # Add test tables with a typical e-commerce structure
        # Main tables
        customers = database.get_or_create_table("customers", "public")
        customers.get_or_create_column("customer_id", "TEXT", is_primary_key=True)
        customers.get_or_create_column("name", "TEXT")
        customers.get_or_create_column("email", "TEXT")
        
        products = database.get_or_create_table("products", "public")
        products.get_or_create_column("product_id", "TEXT", is_primary_key=True)
        products.get_or_create_column("name", "TEXT")
        products.get_or_create_column("price", "DECIMAL")
        
        orders = database.get_or_create_table("orders", "public")
        orders.get_or_create_column("order_id", "TEXT", is_primary_key=True)
        orders.get_or_create_column("customer_id", "TEXT")  # FK to customers
        orders.get_or_create_column("order_date", "TIMESTAMP")
        
        # Related tables
        order_items = database.get_or_create_table("order_items", "public")
        order_items.get_or_create_column("item_id", "TEXT", is_primary_key=True)
        order_items.get_or_create_column("order_id", "TEXT")  # FK to orders
        order_items.get_or_create_column("product_id", "TEXT")  # FK to products
        order_items.get_or_create_column("quantity", "INTEGER")
        
        order_payments = database.get_or_create_table("order_payments", "public")
        order_payments.get_or_create_column("payment_id", "TEXT", is_primary_key=True)
        order_payments.get_or_create_column("order_id", "TEXT")  # FK to orders
        order_payments.get_or_create_column("amount", "DECIMAL")
        
    def _get_test_table_data(self, database_name):
        """Get test table data for syncing schema"""
        return {
            "tables": [
                {
                    "name": "customers",
                    "schema": "public",
                    "columns": [
                        {"name": "customer_id", "data_type": "TEXT", "is_primary_key": True},
                        {"name": "name", "data_type": "TEXT"},
                        {"name": "email", "data_type": "TEXT"}
                    ]
                },
                {
                    "name": "products",
                    "schema": "public",
                    "columns": [
                        {"name": "product_id", "data_type": "TEXT", "is_primary_key": True},
                        {"name": "name", "data_type": "TEXT"},
                        {"name": "price", "data_type": "DECIMAL"}
                    ]
                },
                {
                    "name": "orders",
                    "schema": "public",
                    "columns": [
                        {"name": "order_id", "data_type": "TEXT", "is_primary_key": True},
                        {"name": "customer_id", "data_type": "TEXT"},
                        {"name": "order_date", "data_type": "TIMESTAMP"}
                    ]
                },
                {
                    "name": "order_items",
                    "schema": "public",
                    "columns": [
                        {"name": "item_id", "data_type": "TEXT", "is_primary_key": True},
                        {"name": "order_id", "data_type": "TEXT"},
                        {"name": "product_id", "data_type": "TEXT"},
                        {"name": "quantity", "data_type": "INTEGER"}
                    ]
                },
                {
                    "name": "order_payments",
                    "schema": "public",
                    "columns": [
                        {"name": "payment_id", "data_type": "TEXT", "is_primary_key": True},
                        {"name": "order_id", "data_type": "TEXT"},
                        {"name": "amount", "data_type": "DECIMAL"}
                    ]
                }
            ]
        }

    async def create_csv_database(
        self,
        request: CreateCSVDatabaseRequestDTO,
        csv_files: List[UploadFile]
    ) -> CSVDatabaseDTO:
        """Create/Connect to a CSV database"""
        try:
            # Check if database already exists
            try:
                existing_db = Database.nodes.get(name=request.database_name, user_id=request.user_id)
                if existing_db.type != DatabaseType.CSV.value:
                    raise HTTPException(
                        status_code=400,
                        detail=f"Database '{request.database_name}' exists but is not a CSV database"
                    )
                
                if existing_db.user_id != request.user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have access to this database"
                    )
                
                # Return existing database info
                return CSVDatabaseDTO(
                    uid=existing_db.uid,
                    name=existing_db.name,
                    type=existing_db.type,
                    description=existing_db.description,
                    user_id=existing_db.user_id,
                    integration_id=existing_db.integration_id,
                    is_active=existing_db.is_active,
                    created_at=existing_db.created_at,
                    updated_at=existing_db.updated_at,
                    tables=[
                        CSVTableDTO(
                            uid=table.uid,
                            name=table.name,
                            schema_name=table.schema,
                            description=table.description,
                            columns=[
                                ColumnDTO(
                                    uid=col.uid,
                                    name=col.name,
                                    data_type=col.data_type,
                                    description=col.description,
                                    is_primary_key=col.is_primary_key,
                                    is_nullable=col.is_nullable,
                                    default=col.default,
                                    stats=col.stats
                                ) for col in table.columns.all()
                            ],
                            row_count=table.row_count,
                            last_updated=table.last_updated,
                            storage_url=table.storage_url if hasattr(table, 'storage_url') else None,
                            storage_bucket=table.storage_bucket if hasattr(table, 'storage_bucket') else "",
                            storage_path=table.storage_path if hasattr(table, 'storage_path') else ""
                        ) for table in existing_db.tables.all()
                    ]
                )
                
            except Database.DoesNotExist:
                # Create database node if it doesn't exist
                database = await get_or_create_database(
                    name=request.database_name,
                    description=request.description,
                    db_type=DatabaseType.CSV.value,
                    user_id=request.user_id
                )
                
                # Create placeholder credentials for CSV database
                credentials = DatabaseCredential.create_credentials(
                    integration_id=database.integration_id,
                    host='localhost',  # Placeholder for CSV
                    port=0,  # Placeholder for CSV
                    user='csv_user',  # Placeholder for CSV
                    password='',  # No password needed for CSV
                    user_id=request.user_id,
                    settings=request.settings
                )
                
                # Connect credentials to database
                database.credentials.connect(credentials)
                
                sync_status = database.get_or_create_sync_status()
                
                if csv_files:
                    sync_status.update_status('in_progress')
                    
                    for file in csv_files:
                        content = await file.read()
                        file_obj = io.BytesIO(content)
                        storage_info = {}
                        
                        # Try S3 upload with better error handling
                        try:
                            s3_file_obj = io.BytesIO(content)
                            object_path = f"csv/{database.name}/{file.filename}"
                            
                            storage_info = await self.s3_client.upload_file(
                                file_obj=s3_file_obj,
                                object_path=object_path,
                                content_type="text/csv"
                            )
                            s3_file_obj.close()
                            self.logger.info(f"Successfully uploaded {file.filename} to S3")
                            
                        except Exception as e:
                            self.logger.error(f"S3 upload failed for {file.filename}: {str(e)}")
                            # Continue with local processing but set a warning in the description
                            storage_info = {
                                'presigned_url': None,
                                'bucket': None,
                                'object_path': None,
                                'warning': f"File processed but S3 upload failed: {str(e)}"
                            }
                        
                        try:
                            df = pd.read_csv(file_obj)
                            table_name = os.path.splitext(file.filename)[0]
                            
                            # Check if table already exists
                            existing_tables = [t.name for t in database.tables.all()]
                            if table_name in existing_tables:
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Table '{table_name}' already exists in the database"
                                )
                            
                            self.logger.info(f"Creating table {table_name}")
                            
                            # Add warning to description if S3 upload failed
                            description = f"Table created from {file.filename}"
                            if 'warning' in storage_info:
                                description += f" ({storage_info['warning']})"
                            
                            table = database.get_or_create_table(
                                name=table_name,
                                description=description,
                                storage_url=storage_info.get('presigned_url'),
                                storage_bucket=storage_info.get('bucket'),
                                storage_path=storage_info.get('object_path'),
                                row_count=len(df)
                            )
                            
                            self.logger.info(f"Created table {table_name}, processing columns")
                            
                            for column in df.columns:
                                data_type = str(df[column].dtype)
                                stats = {
                                    "unique_count": int(df[column].nunique()),
                                    "is_nullable": bool(df[column].isnull().any()),
                                    "min": str(df[column].min()) if pd.api.types.is_numeric_dtype(df[column]) else None,
                                    "max": str(df[column].max()) if pd.api.types.is_numeric_dtype(df[column]) else None,
                                    "mean": float(df[column].mean()) if pd.api.types.is_numeric_dtype(df[column]) else None
                                }
                                
                                table.get_or_create_column(
                                    name=column,
                                    data_type=data_type,
                                    is_nullable=stats["is_nullable"],
                                    stats=stats
                                )
                            
                            self.logger.info(f"Processed columns for table {table_name}")
                            
                        finally:
                            file_obj.close()
                    
                    sync_status.update_status('completed')
                
                # Debug log before fetching relationships
                self.logger.info("Getting tables relationship")
                tables = database.tables
                self.logger.info(f"Tables type: {type(tables)}")
                table_list = tables.all()
                self.logger.info(f"Table list length: {len(table_list)}")
                
                result = CSVDatabaseDTO(
                    uid=database.uid,
                    name=database.name,
                    type=database.type,
                    description=database.description,
                    user_id=database.user_id,
                    integration_id=database.integration_id,
                    is_active=database.is_active,
                    created_at=database.created_at,
                    updated_at=database.updated_at,
                    tables=[
                        CSVTableDTO(
                            uid=table.uid,
                            name=table.name,
                            schema_name=table.schema,
                            description=table.description,
                            columns=[
                                ColumnDTO(
                                    uid=col.uid,
                                    name=col.name,
                                    data_type=col.data_type,
                                    description=col.description,
                                    is_primary_key=col.is_primary_key,
                                    is_nullable=col.is_nullable,
                                    default=col.default,
                                    stats=col.stats
                                ) for col in table.columns.all()
                            ],
                            row_count=table.row_count,
                            last_updated=table.last_updated,
                            storage_url=table.storage_url if hasattr(table, 'storage_url') else None,
                            storage_bucket=table.storage_bucket if hasattr(table, 'storage_bucket') else "",
                            storage_path=table.storage_path if hasattr(table, 'storage_path') else ""
                        ) for table in table_list
                    ]
                )
                
                # Debug log
                self.logger.info(f"Returning database info with {len(result.tables)} tables")
                return result
                
        except Exception as e:
            self.logger.error(f"Error creating CSV database: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_database(self, database_name: str, user_id: str) -> Database:
        """Get a database by name and user_id"""
        try:
            database = Database.nodes.get(name=database_name, user_id=user_id)
            return database
        except Database.DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail=f"Database '{database_name}' not found"
            )

    async def map_csv_schema(self, database_name: str, csv_files: List[dict], user_id: str):
        """Map CSV files schema while preserving relationships"""
        try:
            with neodb_db.transaction:
                # Get database
                database = Database.nodes.get(name=database_name, user_id=user_id)
                
                # Process each CSV file
                table_data = {}
                for file_info in csv_files:
                    df = pd.read_csv(file_info['path'])
                    table_name = file_info.get('table_name') or os.path.splitext(os.path.basename(file_info['path']))[0]
                    
                    # Infer column types and create table data
                    columns = []
                    for col_name in df.columns:
                        col_data = df[col_name].dropna()
                        
                        # Infer data type
                        if col_data.empty:
                            data_type = 'text'
                        elif pd.api.types.is_numeric_dtype(df[col_name]):
                            if df[col_name].apply(lambda x: float(x).is_integer()).all():
                                data_type = 'integer'
                            else:
                                data_type = 'numeric'
                        elif pd.api.types.is_datetime64_any_dtype(df[col_name]):
                            data_type = 'timestamp'
                        elif pd.api.types.is_bool_dtype(df[col_name]):
                            data_type = 'boolean'
                        else:
                            data_type = 'text'
                        
                        # Calculate column statistics
                        stats = {
                            'null_count': int(df[col_name].isnull().sum()),
                            'unique_count': int(df[col_name].nunique()),
                            'is_nullable': bool(df[col_name].isnull().any())
                        }
                        
                        # Add type-specific statistics
                        if data_type in ('integer', 'numeric'):
                            non_null = df[col_name].dropna()
                            if len(non_null) > 0:
                                stats.update({
                                    'min': float(non_null.min()),
                                    'max': float(non_null.max()),
                                    'mean': float(non_null.mean()),
                                    'median': float(non_null.median())
                                })
                        elif data_type == 'text':
                            stats.update({
                                'max_length': int(df[col_name].str.len().max() or 0),
                                'avg_length': float(df[col_name].str.len().mean() or 0)
                            })
                        
                        # Detect if column could be a primary key
                        is_primary_key = (stats['unique_count'] == len(df) and 
                                        not stats['is_nullable'])
                        
                        columns.append({
                            'name': col_name,
                            'data_type': data_type,
                            'is_nullable': stats['is_nullable'],
                            'is_primary_key': is_primary_key,
                            'stats': stats
                        })
                    
                    table_data[table_name] = {
                        'schema': 'public',
                        'columns': columns,
                        'properties': {
                            'row_count': len(df),
                            'storage_bucket': file_info.get('bucket', ''),
                            'storage_path': file_info.get('path', ''),
                            'storage_url': file_info.get('url', '')
                        }
                    }
                
                # First sync tables and columns
                database.sync_schema(table_data)
                
                # Cache tables for faster lookups
                table_cache = {table.name: table for table in database.tables.all()}
                
                # Detect relationships between tables
                csv_relationships_added = 0
                for table1_name, table1_info in table_data.items():
                    table1 = table_cache.get(table1_name)
                    if not table1:
                        continue
                        
                    for table2_name, table2_info in table_data.items():
                        if table1_name >= table2_name:  # Skip self and already processed pairs
                            continue
                            
                        table2 = table_cache.get(table2_name)
                        if not table2:
                            continue
                        
                        # Find shared column names
                        shared_columns = set(col['name'] for col in table1_info['columns']) & \
                                       set(col['name'] for col in table2_info['columns'])
                        
                        if shared_columns:
                            self.logger.info(f"[CSV FK Detection] Found shared columns between '{table1_name}' and '{table2_name}': {', '.join(shared_columns)}")
                            
                        for shared_col in shared_columns:
                            # Get column info
                            col1 = next(c for c in table1_info['columns'] if c['name'] == shared_col)
                            col2 = next(c for c in table2_info['columns'] if c['name'] == shared_col)
                            
                            # If one column is unique and not nullable, it might be a foreign key
                            if col1['stats']['unique_count'] == table_data[table1_name]['properties']['row_count'] and \
                               not col1['stats']['is_nullable']:
                                self.logger.info(f"[CSV FK Detection] Detected potential relationship: {table2_name}.{shared_col} -> {table1_name}.{shared_col}")
                                table2.add_foreign_key(table1, shared_col, shared_col, 'ONE_TO_MANY')
                                csv_relationships_added += 1
                            elif col2['stats']['unique_count'] == table_data[table2_name]['properties']['row_count'] and \
                                 not col2['stats']['is_nullable']:
                                self.logger.info(f"[CSV FK Detection] Detected potential relationship: {table1_name}.{shared_col} -> {table2_name}.{shared_col}")
                                table1.add_foreign_key(table2, shared_col, shared_col, 'ONE_TO_MANY')
                                csv_relationships_added += 1
                            else:
                                # Add shared column relationship
                                self.logger.info(f"[CSV FK Detection] Adding shared column relationship between {table1_name}.{shared_col} and {table2_name}.{shared_col}")
                                table1.add_shared_column_relationship(table2, shared_col)
                                table2.add_shared_column_relationship(table1, shared_col)
                
                # Look for columns that follow foreign key naming patterns (e.g. customer_id in orders)
                self.logger.info("[CSV FK Detection] Looking for foreign key naming patterns...")
                for table1_name, table1_info in table_data.items():
                    table1 = table_cache.get(table1_name)
                    if not table1:
                        continue
                    
                    # Collect column names and potential foreign key references
                    table1_cols = {col['name']: col for col in table1_info['columns']}
                    
                    # Find columns that might reference other tables
                    for col_name, col_info in table1_cols.items():
                        # Skip primary key columns
                        if col_info.get('is_primary_key'):
                            continue
                            
                        # Check for _id suffix suggesting a foreign key
                        if col_name.endswith('_id'):
                            # Extract potential table name (e.g. "customer" from "customer_id")
                            potential_table_name = col_name[:-3]  # Remove "_id"
                            self.logger.info(f"[CSV FK Detection] Found potential FK column '{col_name}' in table '{table1_name}', referencing '{potential_table_name}'")
                            
                            # Check for plural form (customers -> customer_id)
                            if potential_table_name + 's' in table_cache:
                                ref_table_name = potential_table_name + 's'
                                self.logger.info(f"[CSV FK Detection] Found plural match: '{potential_table_name}' -> '{ref_table_name}'")
                            # Direct match
                            elif potential_table_name in table_cache:
                                ref_table_name = potential_table_name
                                self.logger.info(f"[CSV FK Detection] Found direct match: '{potential_table_name}'")
                            else:
                                # Try other forms or variations
                                continue
                            
                            ref_table = table_cache.get(ref_table_name)
                            if not ref_table:
                                continue
                                
                            # Find primary key in referenced table
                            ref_table_cols = {col['name']: col for col in table_data[ref_table_name]['columns']}
                            pk_cols = [name for name, col in ref_table_cols.items() if col.get('is_primary_key')]
                            
                            if pk_cols:
                                pk_name = pk_cols[0]
                                self.logger.info(f"[CSV FK Detection] Adding FK from naming pattern: {table1_name}.{col_name} -> {ref_table_name}.{pk_name}")
                                table1.add_foreign_key(ref_table, col_name, pk_name, 'ONE_TO_MANY')
                                csv_relationships_added += 1
                            elif 'id' in ref_table_cols:
                                self.logger.info(f"[CSV FK Detection] Adding FK using 'id' column: {table1_name}.{col_name} -> {ref_table_name}.id")
                                table1.add_foreign_key(ref_table, col_name, 'id', 'ONE_TO_MANY')
                                csv_relationships_added += 1

                self.logger.info(f"[CSV FK Detection] Added {csv_relationships_added} basic foreign key relationships from shared columns and naming patterns")
                
                # After establishing basic relationships based on exact matches,
                # run the enhanced foreign key inference to detect additional relationships
                # based on naming patterns
                self.logger.info("[CSV FK Inference] Running enhanced foreign key inference for CSV database")
                try:
                    inferred_count = database.infer_foreign_key_relationships()
                    self.logger.info(f"[CSV FK Inference] Inferred {inferred_count} additional foreign key relationships")
                    
                    # Log a summary of all relationships
                    total_relationships = csv_relationships_added + inferred_count
                    self.logger.info(f"[CSV FK Summary] Total relationships established: {total_relationships}")
                    self.logger.info(f"[CSV FK Summary] - From shared columns and naming patterns: {csv_relationships_added}")
                    self.logger.info(f"[CSV FK Summary] - From advanced inference: {inferred_count}")
                    
                    # Log the specific relationships
                    self.logger.info("[CSV FK Summary] Relationship details:")
                    for table in database.tables.all():
                        for fk_rel in table.foreign_keys.all():
                            target_table = fk_rel.end_node()
                            rel_props = fk_rel.properties()
                            self.logger.info(f"[CSV FK Summary] {table.name}.{rel_props.get('from_column')} -> {target_table.name}.{rel_props.get('to_column')} ({rel_props.get('type')})")
                except Exception as e:
                    self.logger.warning(f"[CSV FK Inference] Error during enhanced foreign key inference: {str(e)}")
                    self.logger.error(e)
                
                return True
                
        except Exception as e:
            self.logger.error(f"Error mapping CSV schema: {str(e)}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to map CSV schema: {str(e)}"
            )

    async def get_database_by_uid(self, database_uid: str, include_deleted: bool = False) -> Database:
        """Get a database by its UID"""
        try:
            database = Database.nodes.get(uid=database_uid)
            if include_deleted or not database.is_deleted:
                return database
            else:
                raise Database.DoesNotExist("Database is marked as deleted")
        except Database.DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail=f"Database with UID '{database_uid}' not found"
            )

    async def get_database_connection_details(self, database_uid: str) -> Dict[str, Any]:
        """Get database connection details"""
        try:
            # Get database node
            database = await self.get_database_by_uid(database_uid, include_deleted=False)
            
            # Get credentials via Cypher query
            query = """
            MATCH (d:Database {uid: $database_uid})-[:HAS_CREDENTIALS]->(c:DatabaseCredential)
            RETURN c
            """
            
            results, _ = db.cypher_query(query, {'database_uid': database_uid})
            
            if not results or not results[0] or not results[0][0]:
                self.logger.error(f"No credentials found for database {database_uid}")
                raise ValueError(f"No credentials found for database {database_uid}")
            
            # Convert results to a dictionary
            cred_node = results[0][0]
            
            # Parse database type to standardized format
            db_type = database.type.upper() if database.type else "UNKNOWN"
            
            # Handle different database types
            if db_type == "POSTGRES" or db_type == "POSTGRESQL" or database.type.lower() == "postgres":
                # PostgreSQL connection details - using dictionary-style access for Neo4j node properties
                connection_details = {
                    'host': cred_node['host'],
                    'port': int(cred_node['port']),  # Convert port to integer
                    'user': cred_node['user'],
                    'password': cred_node['password'],  # Using direct password access instead of get_password method
                    'database_name': database.name,
                    'database_type': 'POSTGRES',
                    'name': database.name
                }
                self.logger.info(f"Retrieved connection details for PostgreSQL database {database.name}")
                return connection_details
            else:
                self.logger.warning(f"Unknown database type: {database.type}")
                # Return the details anyway, but with a warning - using dictionary-style access
                connection_details = {
                    'host': cred_node['host'],
                    'port': int(cred_node['port']),  # Convert port to integer
                    'user': cred_node['user'],
                    'password': cred_node['password'],  # Using direct password access
                    'database_name': database.name,
                    'database_type': database.type,
                    'name': database.name
                }
                return connection_details
                
        except Exception as e:
            self.logger.error(f"Error getting database connection details: {str(e)}")
            raise

    def standardize_connection_parameters(self, connection_details: Dict[str, Any]) -> Dict[str, Any]:
        """
        Standardize connection parameters to ensure consistent naming
        and validate that all required parameters are present.
        
        Args:
            connection_details: Original connection details dictionary
            
        Returns:
            Standardized connection details dictionary
            
        Raises:
            ValueError: If required parameters are missing
        """
        if not connection_details:
            raise ValueError("Connection details dictionary is empty")
            
        # Create a new dictionary with standardized parameter names
        standardized = {}
        
        # Map for parameter name variations
        param_mapping = {
            # Standard name -> list of possible source names in order of preference
            'host': ['host', 'hostname', 'server', 'server_host'],
            'port': ['port', 'server_port'],
            'user': ['user', 'username', 'user_name', 'uid'],
            'password': ['password', 'pwd', 'pass'],
            'dbname': ['dbname', 'database_name', 'database', 'db', 'name'],
            'database_type': ['database_type', 'db_type', 'type']
        }
        
        # Process each standard parameter
        for std_name, source_names in param_mapping.items():
            # Try each possible source name
            for source_name in source_names:
                if source_name in connection_details and connection_details[source_name] is not None:
                    standardized[std_name] = connection_details[source_name]
                    break
        
        # Validate required parameters
        required_params = ['host', 'port', 'user', 'password', 'dbname']
        missing_params = [param for param in required_params if param not in standardized]
        
        if missing_params:
            error_msg = f"Missing required connection parameters: {', '.join(missing_params)}"
            self.logger.error(error_msg)
            raise ValueError(error_msg)
            
        # Ensure port is an integer
        if 'port' in standardized and not isinstance(standardized['port'], int):
            try:
                standardized['port'] = int(standardized['port'])
            except (ValueError, TypeError):
                self.logger.warning(f"Invalid port value: {standardized['port']}. Using default 5432.")
                standardized['port'] = 5432
                
        return standardized

    async def get_database_schema_from_neo4j(self, database_uid: str, table_uid: Optional[str] = None):
        """Get schema information for a database from Neo4j"""
        try:
            self.logger.info(f"Getting schema from Neo4j for database_uid: {database_uid}")
            database = await self.get_database_by_uid(database_uid)
            
            tables = []
            # Get tables related to this database
            if table_uid:
                tables = [await self.get_table_by_uid_internal(table_uid)]
            else:
                tables = await self.get_tables_for_database(database_uid)
            
            schema = {
                "database_name": database.name,
                "database_type": database.type,
                "tables": [],
                "relationships": []  # Add relationships to schema
            }
            
            # Add table information
            for table in tables:
                columns = await self.get_columns_for_table(table.uid)
                table_info = {
                    "table_name": table.name,
                    "table_uid": table.uid,
                    "columns": [
                        {
                            "name": column.name,
                            "data_type": column.data_type,
                            "description": column.description,
                            "is_primary_key": column.is_primary_key,
                            "is_nullable": column.is_nullable,
                            "is_foreign_key": column.is_foreign_key,
                            "references_table": column.references_table if column.is_foreign_key else None,
                            "references_column": column.references_column if column.is_foreign_key else None
                        }
                        for column in columns
                    ]
                }
                schema["tables"].append(table_info)
                
                # Add relationships from this table - safely handling potential missing methods
                try:
                    # Process foreign key relationships
                    if hasattr(table, 'foreign_keys') and callable(getattr(table, 'foreign_keys', None)):
                        for rel in table.foreign_keys.all():
                            try:
                                # Safely check if end_node method exists
                                if hasattr(rel, 'end_node') and callable(rel.end_node):
                                    target_table = rel.end_node()
                                    props = rel.properties()
                                    
                                    relationship_info = {
                                        "type": "FOREIGN_KEY",
                                        "from_table": table.name,
                                        "to_table": target_table.name,
                                        "from_column": props.get("from_column"),
                                        "to_column": props.get("to_column")
                                    }
                                    schema["relationships"].append(relationship_info)
                                    self.logger.info(f"Added FOREIGN_KEY relationship: {table.name}.{props.get('from_column')} -> {target_table.name}.{props.get('to_column')}")
                                else:
                                    # Alternative approach if end_node method doesn't exist
                                    # Try to get relationship information from columns
                                    for column in columns:
                                        if column.is_foreign_key and column.references_table:
                                            relationship_info = {
                                                "type": "FOREIGN_KEY",
                                                "from_table": table.name,
                                                "to_table": column.references_table,
                                                "from_column": column.name,
                                                "to_column": column.references_column
                                            }
                                            schema["relationships"].append(relationship_info)
                                            self.logger.info(f"Added FOREIGN_KEY relationship from column data: {table.name}.{column.name} -> {column.references_table}.{column.references_column}")
                            except Exception as rel_e:
                                self.logger.warning(f"Error processing relationship from table {table.name}: {str(rel_e)}")
                    else:
                        # If foreign_keys method is not available, try to get relationship info from columns
                        for column in columns:
                            if column.is_foreign_key and column.references_table:
                                relationship_info = {
                                    "type": "FOREIGN_KEY",
                                    "from_table": table.name,
                                    "to_table": column.references_table,
                                    "from_column": column.name,
                                    "to_column": column.references_column
                                }
                                schema["relationships"].append(relationship_info)
                                self.logger.info(f"Added FOREIGN_KEY relationship from column attributes: {table.name}.{column.name} -> {column.references_table}.{column.references_column}")
                    
                    # Process RELATED_TO relationships
                    if hasattr(table, 'relates_to') and callable(getattr(table, 'relates_to', None)):
                        for rel in table.relates_to.all():
                            try:
                                # Safely check if end_node method exists
                                if hasattr(rel, 'end_node') and callable(rel.end_node):
                                    target_table = rel.end_node()
                                    props = rel.properties()
                                    
                                    relationship_info = {
                                        "type": "RELATED_TO",
                                        "from_table": table.name,
                                        "to_table": target_table.name,
                                        "from_column": props.get("from_column", ""),
                                        "to_column": props.get("to_column", ""),
                                        "via": props.get("via", "")  # Keep the 'via' property for additional context
                                    }
                                    schema["relationships"].append(relationship_info)
                                    self.logger.info(f"Added RELATED_TO relationship: {table.name} -> {target_table.name} via {props.get('via', '')}")
                            except Exception as rel_e:
                                self.logger.warning(f"Error processing RELATED_TO relationship from table {table.name}: {str(rel_e)}")
                except Exception as table_rel_e:
                    self.logger.warning(f"Error processing relationships for table {table.name}: {str(table_rel_e)}")
            
            self.logger.info(f"Retrieved schema with {len(schema['tables'])} tables and {len(schema['relationships'])} relationships")
            return schema
        except Exception as e:
            self.logger.error(f"Error getting schema from Neo4j for database {database_uid}: {str(e)}")
            raise

    async def get_tables_for_database(self, database_uid: str) -> List[Table]:
        """Get all tables related to a database"""
        try:
            self.logger.info(f"Getting tables for database: {database_uid}")
            database = await self.get_database_by_uid(database_uid)
            
            # Using the relationship to query tables
            tables = database.tables.all()
            
            if not tables:
                self.logger.warning(f"No tables found for database: {database_uid}")
            
            return tables
        except Exception as e:
            self.logger.error(f"Error getting tables for database {database_uid}: {str(e)}")
            raise

    async def get_columns_for_table(self, table_uid: str) -> List[Column]:
        """Get all columns for a table"""
        try:
            self.logger.info(f"Getting columns for table: {table_uid}")
            table = Table.nodes.get(uid=table_uid)
            
            # Using the relationship to query columns
            columns = table.columns.all()
            
            if not columns:
                self.logger.warning(f"No columns found for table: {table_uid}")
            
            return columns
        except Table.DoesNotExist:
            self.logger.error(f"Table with UID {table_uid} does not exist")
            raise HTTPException(
                status_code=404,
                detail=f"Table with UID '{table_uid}' not found"
            )
        except Exception as e:
            self.logger.error(f"Error getting columns for table {table_uid}: {str(e)}")
            raise

    async def get_table_by_uid(self, database_uid: str, table_uid: str) -> TableDTO:
        """Get a table by its UID within a database"""
        try:
            database = Database.nodes.get(uid=database_uid)
            table = Table.nodes.get(uid=table_uid)
            
            # Verify table belongs to database
            if not database.tables.is_connected(table):
                raise HTTPException(
                    status_code=404,
                    detail=f"Table with UID '{table_uid}' not found in database '{database_uid}'"
                )
            
            return TableDTO(
                uid=table.uid,
                name=table.name,
                schema_name=table.schema,
                columns=[
                    ColumnDTO(
                        uid=col.uid,
                        name=col.name,
                        data_type=col.data_type,
                        description=col.description,
                        is_primary_key=col.is_primary_key,
                        is_nullable=col.is_nullable,
                        default=col.default,
                        stats=col.stats
                    ) for col in table.columns.all()
                ],
                description=table.description,
                row_count=table.row_count,
                last_updated=table.last_updated
            )
        except Database.DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail=f"Database with UID '{database_uid}' not found"
            )
        except Table.DoesNotExist:
            raise HTTPException(
                status_code=404,
                detail=f"Table with UID '{table_uid}' not found"
            )
        except Exception as e:
            self.logger.error(f"Error getting table by UID: {e!s}")
            raise HTTPException(status_code=500, detail=str(e))

    async def add_csv_files(
        self,
        database_uid: str,
        user_id: str,
        csv_files: List[UploadFile]
    ) -> CSVDatabaseDTO:
        """Add more CSV files to an existing database"""
        try:
            # Get database by UID
            try:
                database = Database.nodes.get(uid=database_uid)
                if database.type != DatabaseType.CSV.value:
                    raise ValueError(f"Database {database_uid} is not a CSV database")
                
                if database.user_id != user_id:
                    raise HTTPException(
                        status_code=403,
                        detail="You don't have access to this database"
                    )
                
                sync_status = database.get_or_create_sync_status()
                
                if csv_files:
                    sync_status.update_status('in_progress')
                    
                    for file in csv_files:
                        content = await file.read()
                        file_obj = io.BytesIO(content)
                        storage_info = {}
                        
                        # Try S3 upload with better error handling
                        try:
                            s3_file_obj = io.BytesIO(content)
                            object_path = f"csv/{database.name}/{file.filename}"
                            
                            storage_info = await self.s3_client.upload_file(
                                file_obj=s3_file_obj,
                                object_path=object_path,
                                content_type="text/csv"
                            )
                            s3_file_obj.close()
                            self.logger.info(f"Successfully uploaded {file.filename} to S3")
                            
                        except Exception as e:
                            self.logger.error(f"S3 upload failed for {file.filename}: {str(e)}")
                            # Continue with local processing but set a warning in the description
                            storage_info = {
                                'presigned_url': None,
                                'bucket': None,
                                'object_path': None,
                                'warning': f"File processed but S3 upload failed: {str(e)}"
                            }
                        
                        try:
                            df = pd.read_csv(file_obj)
                            table_name = os.path.splitext(file.filename)[0]
                            
                            # Check if table already exists
                            existing_tables = [t.name for t in database.tables.all()]
                            if table_name in existing_tables:
                                raise HTTPException(
                                    status_code=400,
                                    detail=f"Table '{table_name}' already exists in the database"
                                )
                            
                            self.logger.info(f"Creating table {table_name}")
                            
                            # Add warning to description if S3 upload failed
                            description = f"Table created from {file.filename}"
                            if 'warning' in storage_info:
                                description += f" ({storage_info['warning']})"
                            
                            table = database.get_or_create_table(
                                name=table_name,
                                description=description,
                                storage_url=storage_info.get('presigned_url'),
                                storage_bucket=storage_info.get('bucket'),
                                storage_path=storage_info.get('object_path'),
                                row_count=len(df)
                            )
                            
                            self.logger.info(f"Created table {table_name}, processing columns")
                            
                            for column in df.columns:
                                data_type = str(df[column].dtype)
                                stats = {
                                    "unique_count": int(df[column].nunique()),
                                    "is_nullable": bool(df[column].isnull().any()),
                                    "min": str(df[column].min()) if pd.api.types.is_numeric_dtype(df[column]) else None,
                                    "max": str(df[column].max()) if pd.api.types.is_numeric_dtype(df[column]) else None,
                                    "mean": float(df[column].mean()) if pd.api.types.is_numeric_dtype(df[column]) else None
                                }
                                
                                table.get_or_create_column(
                                    name=column,
                                    data_type=data_type,
                                    is_nullable=stats["is_nullable"],
                                    stats=stats
                                )
                            
                            self.logger.info(f"Processed columns for table {table_name}")
                            
                        finally:
                            file_obj.close()
                    
                    sync_status.update_status('completed')
                
                # Return updated database info
                return CSVDatabaseDTO(
                    uid=database.uid,
                    name=database.name,
                    type=database.type,
                    description=database.description,
                    user_id=database.user_id,
                    integration_id=database.integration_id,
                    is_active=database.is_active,
                    created_at=database.created_at,
                    updated_at=database.updated_at,
                    tables=[
                        CSVTableDTO(
                            uid=table.uid,
                            name=table.name,
                            schema_name=table.schema,
                            description=table.description,
                            columns=[
                                ColumnDTO(
                                    uid=col.uid,
                                    name=col.name,
                                    data_type=col.data_type,
                                    description=col.description,
                                    is_primary_key=col.is_primary_key,
                                    is_nullable=col.is_nullable,
                                    default=col.default,
                                    stats=col.stats
                                ) for col in table.columns.all()
                            ],
                            row_count=table.row_count,
                            last_updated=table.last_updated,
                            storage_url=table.storage_url if hasattr(table, 'storage_url') else None,
                            storage_bucket=table.storage_bucket if hasattr(table, 'storage_bucket') else "",
                            storage_path=table.storage_path if hasattr(table, 'storage_path') else ""
                        ) for table in database.tables.all()
                    ]
                )
                
            except Database.DoesNotExist:
                raise HTTPException(
                    status_code=404,
                    detail=f"Database with UID '{database_uid}' not found"
                )
                
        except HTTPException:
            raise
        except Exception as e:
            self.logger.error(f"Error adding CSV files: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def save_database(self, database: Any) -> None:
        """Save database changes to Neo4j"""
        try:
            # Save the database node
            database.save()
            
            # Save all tables
            for table in database.tables.all():
                table.save()
                
                # Save all columns for each table
                for column in table.columns.all():
                    column.save()
                    
            self.logger.info(f"Successfully saved database {database.name} with all its tables and columns")
        except Exception as e:
            self.logger.error(f"Error saving database: {str(e)}")
            raise

    async def get_table_schema_from_neo4j(self, table_uid: str) -> Dict[str, Any]:
        """Get schema information for a specific table from Neo4j"""
        try:
            self.logger.info(f"Getting schema from Neo4j for table_uid: {table_uid}")
            
            # Get the table info
            table = await self.get_table_by_uid_internal(table_uid)
            
            # Get columns for this table
            columns = await self.get_columns_for_table(table_uid)
            
            schema = {
                "table_name": table.name,
                "table_uid": table.uid,
                "table_type": "CSV" if hasattr(table, 'storage_url') else "SQL",
                "database_name": table.database.single().name if table.database.single() else "Unknown",
                "database_uid": table.database.single().uid if table.database.single() else None,
                "columns": [
                    {
                        "name": column.name,
                        "data_type": column.data_type,
                        "description": column.description,
                        "is_nullable": column.is_nullable
                    }
                    for column in columns
                ]
            }
            
            return schema
        except Exception as e:
            self.logger.error(f"Error getting schema from Neo4j for table {table_uid}: {str(e)}")
            raise

    async def get_table_by_uid_internal(self, table_uid: str) -> Table:
        """Get a table by its UID without requiring database UID"""
        try:
            self.logger.info(f"Getting table by UID (internal): {table_uid}")
            table = Table.nodes.get(uid=table_uid)
            return table
        except Table.DoesNotExist:
            self.logger.error(f"Table with UID {table_uid} does not exist")
            raise HTTPException(
                status_code=404,
                detail=f"Table with UID '{table_uid}' not found"
            )
            
    async def query(self, database_uid: str, sql: str, params: Optional[Dict[str, Any]] = None):
        """Execute query on database and return results"""
        try:
            # Check for missing or empty SQL
            if not sql or not sql.strip():
                self.logger.error("Empty SQL query provided")
                return []

            # Extract actual SQL if we're given an object
            actual_sql = sql
            if not isinstance(sql, str):
                # Handle objects with a code attribute (like CodeGenerationResult)
                if hasattr(sql, 'code') and isinstance(sql.code, str):
                    actual_sql = sql.code
                    self.logger.info(f"Extracted SQL from object: {actual_sql[:100]}...")
            elif "AgentRunResult" in sql:
                # Handle AgentRunResult objects serialized as strings
                try:
                    import re
                    # Attempt to extract the SQL code from the string representation
                    match = re.search(r"code='(.*?)'", sql, re.DOTALL)
                    if match:
                        actual_sql = match.group(1)
                        self.logger.info(f"Extracted SQL: {actual_sql[:100]}...")
                    else:
                        self.logger.warning("Could not extract SQL from AgentRunResult - no code= found")
                except Exception as ex:
                    self.logger.error(f"Error extracting SQL from AgentRunResult: {str(ex)}")
            
            # Get connection details for the database
            connection_details = await self.get_database_connection_details(database_uid)
            if not connection_details:
                self.logger.error(f"Could not retrieve connection details for database {database_uid}")
                raise ValueError(f"Connection details not found for database {database_uid}")
            
            # Standardize and validate connection parameters
            try:
                std_conn_details = self.standardize_connection_parameters(connection_details)
                self.logger.info(f"Standardized connection parameters: host={std_conn_details.get('host')}, "
                                f"port={std_conn_details.get('port')}, "
                                f"dbname={std_conn_details.get('dbname')}, "
                                f"user={std_conn_details.get('user')}")
            except ValueError as ve:
                self.logger.error(f"Invalid connection parameters: {str(ve)}")
                raise
            
            self.logger.info(f"Attempting to connect to real database and execute query")
            
            try:
                # Create a connection to the database
                import psycopg2
                import psycopg2.extras
                
                # Add debug logging
                self.logger.info(f"SQL query to execute: {actual_sql}")
                
                # Try to connect with explicit options using standardized parameters
                conn = psycopg2.connect(
                    host=std_conn_details['host'],
                    port=std_conn_details['port'],
                    dbname=std_conn_details['dbname'],
                    user=std_conn_details['user'],
                    password=std_conn_details['password'],
                    options="-c search_path=public"  # Explicitly set search_path
                )
                
                # Debug: Check search_path after connection
                with conn.cursor() as debug_cursor:
                    debug_cursor.execute("SHOW search_path;")
                    search_path = debug_cursor.fetchone()[0]
                    self.logger.info(f"Database search_path: {search_path}")
                    
                    # Debug: List tables in public schema
                    debug_cursor.execute("""
                        SELECT table_name FROM information_schema.tables 
                        WHERE table_schema = 'public'
                        ORDER BY table_name LIMIT 10
                    """)
                    tables = debug_cursor.fetchall()
                    table_list = [t[0] for t in tables]
                    self.logger.info(f"Tables in public schema: {', '.join(table_list)}")
                
                # Execute the query
                with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cursor:
                    cursor.execute(actual_sql)  # Use the extracted SQL
                    rows = cursor.fetchall()
                    
                conn.close()
                
                self.logger.info(f"Query executed successfully on real database, returned {len(rows)} rows")
                return list(rows)
                
            except Exception as db_error:
                self.logger.error(f"Error while executing query: {str(db_error)}")
                sql_execution_error = {
                    "type": "sql_execution_error",
                    "message": str(db_error),
                    "sql": actual_sql
                }
                raise Exception(sql_execution_error)

        except Exception as e:
            self.logger.error(f"AnalyticsRepository.query - Error executing query: {str(e)}")
            raise
