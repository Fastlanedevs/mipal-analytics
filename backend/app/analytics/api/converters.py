from typing import List, Optional, Dict, Any, Tuple, Union
from datetime import datetime

from app.analytics.api.dto import (
    DatabaseDTO,
    PostgresDatabaseDTO,
    TableDTO,
    ColumnDTO,
    CSVDatabaseDTO,
    CSVTableDTO,
    PostgresSchemaDTO,
    PostgresTableDTO,
    PostgresColumnDTO,
    DashboardResponseDTO,
    DashboardListResponseDTO,
    DataframeResponseDTO
)
from app.analytics.entity.analytics import Database, Table, Column, DatabaseType
from app.analytics.entity.dataframe import Dataframe as DataframeEntity
from app.analytics.repository.schema.models.dashboard import Dashboard
from app.analytics.repository.schema.models.dataframe import Dataframe as DBDataframe

class DTOConverter:
    """Converts between DTOs and entities"""
    
    # Dashboard conversion methods
    @staticmethod
    def to_dashboard_dto(dashboard: Dashboard) -> DashboardResponseDTO:
        """Convert Dashboard entity to DashboardResponseDTO"""
        # Get the charts from the relationship
        charts = []
        try:
            # Get charts from the relationship
            from neomodel import db
            
            # Query to get all charts for this dashboard
            # Use a more direct approach that doesn't depend on labels
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[:CONTAINS_CHART]->(c)
            WHERE c.uid IS NOT NULL
            RETURN c.uid as id, c.title as title, c.description as description, 
                   c.chart_type as chart_type, c.chart_schema as chart_schema,
                   c.chart_data as chart_data, c.message_id as message_id
            """
            
            results, meta = db.cypher_query(query, {'dashboard_id': dashboard.dashboard_id})
            
            # Process results
            if results and len(results) > 0:
                # Convert results to chart info objects
                for row in results:
                    chart_info = {
                        "id": row[0] if row[0] is not None else "",
                        "title": row[1] if row[1] is not None else "",
                        "description": row[2] if row[2] is not None else "",
                        "chart_type": row[3] if row[3] is not None else "",
                        "chart_schema": row[4] if row[4] is not None else {},
                        "chart_data": row[5] if row[5] is not None else [],
                        "message_id": row[6] if row[6] is not None else None
                    }
                    # Only add the chart if it has valid data
                    if chart_info["id"]:
                        charts.append(chart_info)
        except Exception as e:
            # Log error but continue
            import logging
            logging.error(f"Error retrieving charts for dashboard {dashboard.dashboard_id}: {str(e)}")
        
        # Get the dataframes from the relationship
        dataframes = []
        try:
            # Get dataframes from the relationship
            from neomodel import db
            
            # Query to get all dataframes for this dashboard
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[:CONTAINS_DATAFRAME]->(df:Dataframe)
            WHERE df.dataframe_id IS NOT NULL
            RETURN df
            """
            
            results, meta = db.cypher_query(query, {'dashboard_id': dashboard.dashboard_id})
            
            # Process results
            if results and len(results) > 0:
                # Convert results to dataframe objects
                for row in results:
                    db_dataframe = DBDataframe.inflate(row[0])
                    # Convert to entity model then to DTO
                    dataframe_entity = DataframeEntity.from_db_model(db_dataframe)
                    dataframe_dto = DTOConverter.to_dataframe_dto(dataframe_entity)
                    dataframes.append(dataframe_dto)
        except Exception as e:
            # Log error but continue
            import logging
            logging.error(f"Error retrieving dataframes for dashboard {dashboard.dashboard_id}: {str(e)}")
        
        return DashboardResponseDTO(
            dashboard_id=dashboard.dashboard_id,
            title=dashboard.title,
            description=dashboard.description,
            layout_config=dashboard.layout_config,
            layouts=dashboard.layouts,
            charts=charts,
            dataframes=dataframes,
            user_id=dashboard.user_id,
            org_id=dashboard.org_id,
            created_at=datetime.fromisoformat(dashboard.created_at),
            updated_at=datetime.fromisoformat(dashboard.updated_at)
        )

    @staticmethod
    def to_dataframe_dto(dataframe: Union[DBDataframe, DataframeEntity]) -> DataframeResponseDTO:
        """
        Convert Dataframe entity or DB model to DataframeResponseDTO
        
        Args:
            dataframe: Dataframe entity or DB model
            
        Returns:
            DataframeResponseDTO
        """
        if isinstance(dataframe, DataframeEntity):
            # Convert from entity model
            return DataframeResponseDTO(
                dataframe_id=dataframe.dataframe_id,
                content=dataframe.content,
                columns=dataframe.columns,
                metadata=dataframe.metadata,
                user_id=dataframe.user_id,
                message_id=dataframe.message_id,
                created_at=dataframe.created_at,
                updated_at=dataframe.updated_at
            )
        else:
            # Convert from DB model
            return DataframeResponseDTO(
                dataframe_id=dataframe.dataframe_id,
                content=dataframe.content,
                columns=dataframe.columns,
                metadata=dataframe.metadata,
                user_id=dataframe.user_id,
                message_id=dataframe.message_id,
                created_at=datetime.fromisoformat(dataframe.created_at),
                updated_at=datetime.fromisoformat(dataframe.updated_at)
            )

    @staticmethod
    def to_dashboard_list_dto(dashboards: List[Dashboard], total_count: int) -> DashboardListResponseDTO:
        """Convert list of Dashboard entities to DashboardListResponseDTO"""
        return DashboardListResponseDTO(
            items=[DTOConverter.to_dashboard_dto(dashboard) for dashboard in dashboards],
            total=total_count
        )
    
    @staticmethod
    def to_column_dto(column: Column) -> ColumnDTO:
        """Convert Column entity to ColumnDTO"""
        return ColumnDTO(
            uid=column.uid,
            name=column.name,
            data_type=column.data_type,
            description=column.description,
            is_primary_key=column.is_primary_key,
            is_nullable=column.is_nullable,
            default=column.default,
            stats=column.stats
        )

    @staticmethod
    def to_table_dto(table: Table) -> TableDTO:
        """Convert Table entity to TableDTO"""
        # Handle last_updated field safely
        try:
            if isinstance(table.last_updated, str):
                last_updated = table.last_updated
            elif isinstance(table.last_updated, datetime):
                last_updated = table.last_updated.isoformat()
            elif table.last_updated is None:
                last_updated = None
            else:
                last_updated = str(table.last_updated)
        except Exception:
            # Fallback if there's any error
            last_updated = str(table.last_updated) if hasattr(table, 'last_updated') and table.last_updated else None
        
        return TableDTO(
            uid=table.uid,
            name=table.name,
            schema_name=table.schema,
            description=table.description,
            columns=[DTOConverter.to_column_dto(col) for col in table.columns],
            row_count=table.row_count,
            last_updated=last_updated
        )

    @staticmethod
    def to_csv_table_dto(table: Table) -> CSVTableDTO:
        """Convert Table entity to CSVTableDTO"""
        base_dto = DTOConverter.to_table_dto(table)
        return CSVTableDTO(
            **base_dto.dict(),
            storage_url=table.storage_url,
            storage_bucket=table.storage_bucket,
            storage_path=table.storage_path
        )

    @staticmethod
    def to_postgres_table_dto(table: Table) -> PostgresTableDTO:
        """Convert Table entity to PostgresTableDTO"""
        base_dto = DTOConverter.to_table_dto(table)
        # Initialize with base table fields
        params = base_dto.dict()
        # Convert regular columns to PostgresColumnDTOs 
        params["columns"] = [
            PostgresColumnDTO(
                **DTOConverter.to_column_dto(col).dict()
            ) 
            for col in table.columns
        ]
        
        return PostgresTableDTO(**params)

    @staticmethod
    def to_database_dto(database: Database) -> DatabaseDTO:
        """Convert Database entity to DatabaseDTO"""
        # Handle dates that might be strings or datetime objects
        try:
            if isinstance(database.created_at, str):
                created_at = database.created_at
            elif isinstance(database.created_at, datetime):
                created_at = database.created_at.isoformat()
            else:
                created_at = str(database.created_at)
                
            if isinstance(database.updated_at, str):
                updated_at = database.updated_at
            elif isinstance(database.updated_at, datetime): 
                updated_at = database.updated_at.isoformat()
            else:
                updated_at = str(database.updated_at)
        except Exception as e:
            # Last resort fallback to ensure we don't crash
            created_at = str(database.created_at) if hasattr(database, 'created_at') else ""
            updated_at = str(database.updated_at) if hasattr(database, 'updated_at') else ""
        
        # Handle get_active_tables which might work differently between Neo4j and Pydantic models
        tables = []
        try:
            if hasattr(database, 'get_active_tables'):
                # If it's a method, use it
                tables = database.get_active_tables()
            elif hasattr(database, 'tables'):
                # If it's a relationship
                if hasattr(database.tables, 'all'):
                    # It's a Neo4j relationship
                    tables = [t for t in database.tables.all() if not getattr(t, 'is_deleted', False)]
                else:
                    # It's a list property
                    tables = [t for t in database.tables if not getattr(t, 'is_deleted', False)]
        except Exception as e:
            # Fallback to empty list
            tables = []
            
        return DatabaseDTO(
            uid=database.uid,
            name=database.name,
            type=DatabaseType(database.type).value,
            description=database.description,
            tables=[DTOConverter.to_table_dto(table) for table in tables],
            user_id=database.user_id,
            integration_id=database.integration_id,
            is_active=database.is_active,
            created_at=created_at,
            updated_at=updated_at
        )

    @staticmethod
    def to_postgres_database_dto(database: Database) -> PostgresDatabaseDTO:
        """Convert Database entity to PostgresDatabaseDTO"""
        if database.type != DatabaseType.POSTGRES.value:
            raise ValueError("Database is not PostgreSQL type")
            
        base_dto = DTOConverter.to_database_dto(database)
        
        # Get credentials - properly handle credentials as a RelationshipManager
        try:
            # For Neo4j Schema.Database object - use RelationshipManager.single()
            if hasattr(database, 'credentials') and hasattr(database.credentials, 'single'):
                credentials_obj = database.credentials.single()
                credentials = {
                    'host': credentials_obj.host,
                    'port': credentials_obj.port,
                    'user': credentials_obj.user
                }
            # For Pydantic Database entity - credentials is directly a dict 
            else:
                credentials = database.credentials or {}
        except Exception as e:
            # Fallback if relationship access fails
            credentials = {}
        
        # Create a dict from base_dto and update with PostgreSQL specifics
        params = base_dto.dict()
        
        # Handle schemas which might be a relationship or property
        schemas = []
        if hasattr(database, 'schemas'):
            if hasattr(database.schemas, 'all'): 
                # It's a relationship
                schemas_rel = database.schemas.all()
                schemas = [
                    {
                        'name': s.name,
                        'tables': s.tables,
                        'owner': getattr(s, 'owner', None),
                        'privileges': getattr(s, 'privileges', None)
                    } 
                    for s in schemas_rel
                ]
            else:
                # It's a property
                schemas = database.schemas
                
        # Handle get_active_tables which might work differently between Neo4j and Pydantic models
        tables = []
        try:
            if hasattr(database, 'get_active_tables'):
                # If it's a method, use it
                tables = database.get_active_tables()
            elif hasattr(database, 'tables'):
                # If it's a relationship
                if hasattr(database.tables, 'all'):
                    # It's a Neo4j relationship
                    tables = [t for t in database.tables.all() if not t.is_deleted]
                else:
                    # It's a list property
                    tables = [t for t in database.tables if not getattr(t, 'is_deleted', False)]
        except Exception as e:
            # Fallback to empty list
            tables = []
        
        params.update({
            "host": credentials.get('host', 'localhost'),
            "port": int(credentials.get('port', 5432)),
            "user": credentials.get('user', ''),
            "schemas": [
                PostgresSchemaDTO(
                    name=schema['name'],
                    tables=schema['tables'],
                    owner=schema.get('owner'),
                    privileges=schema.get('privileges')
                )
                for schema in schemas
            ] if schemas else None,
            "tables": [DTOConverter.to_postgres_table_dto(table) for table in tables]
        })
        
        return PostgresDatabaseDTO(**params)

    @staticmethod
    def to_csv_database_dto(database: Database) -> CSVDatabaseDTO:
        """Convert Database entity to CSVDatabaseDTO"""
        if database.type != DatabaseType.CSV.value:
            raise ValueError("Database is not CSV type")
            
        base_dto = DTOConverter.to_database_dto(database)
        
        # Handle get_active_tables which might work differently between Neo4j and Pydantic models
        tables = []
        try:
            if hasattr(database, 'get_active_tables'):
                # If it's a method, use it
                tables = database.get_active_tables()
            elif hasattr(database, 'tables'):
                # If it's a relationship
                if hasattr(database.tables, 'all'):
                    # It's a Neo4j relationship
                    tables = [t for t in database.tables.all() if not t.is_deleted]
                else:
                    # It's a list property
                    tables = [t for t in database.tables if not getattr(t, 'is_deleted', False)]
        except Exception as e:
            # Fallback to empty list
            tables = []
        
        # Create a dict from base_dto, but update tables with CSV table DTOs
        params = base_dto.dict()
        params["tables"] = [DTOConverter.to_csv_table_dto(table) for table in tables]
        
        return CSVDatabaseDTO(**params)

    @staticmethod
    def to_database_entity(dto: DatabaseDTO) -> Database:
        """Convert DatabaseDTO to Database entity"""
        return Database(
            uid=dto.uid,
            name=dto.name,
            type=DatabaseType(dto.type),
            description=dto.description,
            user_id=dto.user_id,
            integration_id=dto.integration_id,
            is_active=dto.is_active,
            created_at=datetime.fromisoformat(dto.created_at),
            updated_at=datetime.fromisoformat(dto.updated_at)
        )

    @staticmethod
    def to_table_entity(dto: TableDTO) -> Table:
        """Convert TableDTO to Table entity"""
        return Table(
            uid=dto.uid,
            name=dto.name,
            schema=dto.schema_name,
            description=dto.description,
            columns=[DTOConverter.to_column_entity(col) for col in dto.columns],
            row_count=dto.row_count,
            last_updated=datetime.fromisoformat(dto.last_updated) if dto.last_updated else None
        )

    @staticmethod
    def to_column_entity(dto: ColumnDTO) -> Column:
        """Convert ColumnDTO to Column entity"""
        return Column(
            uid=dto.uid,
            name=dto.name,
            data_type=dto.data_type,
            description=dto.description,
            is_primary_key=dto.is_primary_key,
            is_nullable=dto.is_nullable,
            default=dto.default,
            stats=dto.stats
        ) 