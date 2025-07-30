from typing import List, Optional
from fastapi import UploadFile
import os

from app.analytics.api.dto import (
    DatabaseDTO,
    PostgresDatabaseDTO,
    TableDTO,
    CreatePostgresDatabaseRequestDTO,
    CSVDatabaseDTO,
    CreateCSVDatabaseRequestDTO,
    SchemaResponseDTO,
    RecommendationItemDTO,
    RecommendationResponseDTO,
    ExcelUploadRequestDTO,
    ExcelDatabaseDTO,
    ExcelTableDTO,
    ColumnDTO
)
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.analytics.service.postgres_service import PostgresService
from app.analytics.service.schema_service import SchemaService
from app.analytics.api.converters import DTOConverter
from app.analytics.errors import (
    DatabaseNotFoundError,
    TableNotFoundError,
    UnauthorizedError,
    InvalidOperationError,
    AnalyticsError
)
from pkg.log.logger import Logger
from pkg.db_util.postgres_conn import PostgresConnection
from app.analytics.repository.storage.s3_client import SchemaS3Client
from app.middleware.auth import TokenData
from pkg.llm_provider.llm_client import LLMClient, LLMModel
from app.pal.analytics.utils.agent_logger import AgentLogger
from app.pal.analytics.adapters.analytics_repository_adapter import AnalyticsRepositoryAdapter
from app.pal.analytics.utils.models import convert_to_schema_info
from pkg.redis.client import RedisClient
from app.pal.analytics.utils.models import SchemaInfo

import json
class AnalyticsService:
    """Coordinator service for analytics operations"""
    
    def __init__(self,
        analytics_repository: AnalyticsRepository,
        postgres_service: PostgresService,
        logger: Logger,
        redis_client: RedisClient,
        s3_client: SchemaS3Client,
        llm_client: LLMClient,
    ):
        self.repository = analytics_repository
        self.logger = logger
        # Create service instances
        self.postgres_service = postgres_service
        self.schema_service = SchemaService(analytics_repository=analytics_repository, s3_client=s3_client, logger=logger, llm_client=llm_client)
        self.llm_client = llm_client
        self.redis_client = redis_client

    async def list_databases(self, user_id: str) -> List[DatabaseDTO]:
        """List all mapped databases"""
        return await self.repository.list_databases(user_id)

    async def list_postgres_databases(self) -> List[PostgresDatabaseDTO]:
        """List all PostgreSQL databases"""
        return await self.repository.list_postgres_databases()

    async def get_database_by_uid(self, database_uid: str, include_deleted: bool = False) -> DatabaseDTO:
        """Get database by UID"""
        database = await self.repository.get_database_by_uid(database_uid, include_deleted)
        if not database:
            raise DatabaseNotFoundError(database_uid)
        return DTOConverter.to_database_dto(database)

    async def get_table_by_uid(self, database_uid: str, table_uid: str) -> TableDTO:
        """Get table by UID"""
        database = await self.repository.get_database_by_uid(database_uid)
        if not database:
            raise DatabaseNotFoundError(database_uid)
            
        table = database.get_table_by_uid(table_uid)
        if not table:
            raise TableNotFoundError(table_uid, database.name)
            
        return DTOConverter.to_table_dto(table)

    async def create_postgres_database(self, request: CreatePostgresDatabaseRequestDTO) -> PostgresDatabaseDTO:
        """Create/Connect to a PostgreSQL database and map its schema"""
        # Delegate to PostgreSQL service
        database = await self.postgres_service.create_database(request)
        return DTOConverter.to_postgres_database_dto(database)

    async def create_csv_database(
        self,
        request: CreateCSVDatabaseRequestDTO,
        csv_files: List[UploadFile]
    ) -> CSVDatabaseDTO:
        """Create/Connect to a CSV database and map its schema"""
        # Delegate to Schema service
        database = await self.schema_service.create_database(request, csv_files)
        return DTOConverter.to_csv_database_dto(database)

    async def add_csv_files(
        self,
        database_uid: str,
        user_id: str,
        csv_files: List[UploadFile]
    ) -> CSVDatabaseDTO:
        """Add more CSV files to an existing database"""
        # Get database and verify access
        database = await self.repository.get_database_by_uid(database_uid)
        if not database:
            raise DatabaseNotFoundError(database_uid)
        if database.user_id != user_id:
            raise UnauthorizedError()
            
        # Delegate to Schema service
        updated_database = await self.schema_service.add_files(database, csv_files)
        return DTOConverter.to_csv_database_dto(updated_database)

    async def map_postgres_schema(self, database_name: Optional[str] = None, database_uid: Optional[str] = None, user_id: str = None) -> SchemaResponseDTO:
        """Map PostgreSQL database schema"""
        # Delegate to PostgreSQL service
        return await self.postgres_service.map_schema(database_name=database_name, database_uid=database_uid, user_id=user_id)

    async def soft_delete_table(self, database_uid: str, table_uid: str, user_id: str) -> None:
        """Soft delete a table"""
        database = await self.repository.get_database_by_uid(database_uid)
        if not database:
            raise DatabaseNotFoundError(database_uid)
        if database.user_id != user_id:
            raise UnauthorizedError()
            
        table = database.get_table_by_uid(table_uid)
        if not table:
            raise TableNotFoundError(table_uid, database.name)
        if table.is_deleted:
            raise InvalidOperationError("Table is already deleted")
            
        table.soft_delete()
        await self.repository.save_database(database)

    async def restore_table(self, database_uid: str, table_uid: str, user_id: str) -> None:
        """Restore a soft-deleted table"""
        database = await self.repository.get_database_by_uid(database_uid)
        if not database:
            raise DatabaseNotFoundError(database_uid)
        if database.user_id != user_id:
            raise UnauthorizedError()
            
        table = database.get_table_by_uid(table_uid, include_deleted=True)
        if not table:
            raise TableNotFoundError(table_uid, database.name)
        if not table.is_deleted:
            raise InvalidOperationError("Table is not deleted")
            
        # Check for name conflicts
        if database.get_table_by_name(table.name):
            raise InvalidOperationError(
                f"Cannot restore table: an active table with name '{table.name}' already exists"
            )
            
        table.restore()
        await self.repository.save_database(database)

    async def soft_delete_database(self, database_uid: str, user_id: str) -> None:
        """Soft delete a database and all its tables"""
        database = await self.repository.get_database_by_uid(database_uid)
        if not database:
            raise DatabaseNotFoundError(database_uid)
        if database.user_id != user_id:
            raise UnauthorizedError()
        if database.is_deleted:
            raise InvalidOperationError("Database is already deleted")
            
        database.soft_delete()
        await self.repository.save_database(database)

    async def restore_database(self, database_uid: str, user_id: str, restore_tables: bool = True) -> None:
        """Restore a soft-deleted database"""
        database = await self.repository.get_database_by_uid(database_uid, include_deleted=True)
        if not database:
            raise DatabaseNotFoundError(database_uid)
        if database.user_id != user_id:
            raise UnauthorizedError()
        if not database.is_deleted:
            raise InvalidOperationError("Database is not deleted")
            
        database.restore(restore_tables=restore_tables)
        await self.repository.save_database(database)

    async def get_deleted_tables(self, database_uid: str, user_id: str) -> List[TableDTO]:
        """Get all soft-deleted tables in a database"""
        database = await self.repository.get_database_by_uid(database_uid)
        if not database:
            raise DatabaseNotFoundError(database_uid)
        if database.user_id != user_id:
            raise UnauthorizedError()
            
        deleted_tables = database.get_deleted_tables()
        return [DTOConverter.to_table_dto(table) for table in deleted_tables]

    async def get_recommendations(
        self,
        database_uid: str,
        table_uid: Optional[str] = None,
        count: int = 5,
        user_question: Optional[str] = None,
    ) -> RecommendationResponseDTO:
        """Get query recommendations based on database schema"""
        # Get database info
        db_info = await self.repository.get_database_by_uid(database_uid)
        if not db_info:
            raise DatabaseNotFoundError(f"Database with UID {database_uid} not found")
        
        # Determine database type
        db_type = "unknown"
        if hasattr(db_info, 'type'):
            db_type = db_info.type
        elif hasattr(db_info, 'db_type'):
            db_type = db_info.db_type

        schema_info = await self.get_database_schema(database_uid,table_uid);
        
        if not schema_info:
            raise InvalidOperationError(f"Could not retrieve schema for database {database_uid}")
        
        # Initialize SchemaBasedRecommendationGenerator
        from app.pal.analytics.generators.recommendation_generator import SchemaBasedRecommendationGenerator

        # Create recommendation generator with provided  client
        generator = SchemaBasedRecommendationGenerator(
            llm_client=self.llm_client,
            model="google-gla:gemini-2.0-flash",
            logger=self.logger
        )
        
        # Generate recommendations
        recommendations = await generator.generate_recommendations(
            schema=schema_info.model_dump(),
            database_type=db_type,
            count=count,
            user_question=user_question
        )
        
        # Convert to DTO
        response = RecommendationResponseDTO(
            recommendations=[
                RecommendationItemDTO(
                    title=rec.title,
                    explanation=rec.explanation,
                    question=rec.question,
                    category=rec.category
                ) for rec in recommendations
            ]
        )

        # Get DEV_MODE from environment variables with default to False
        dev_mode = os.environ.get("DEV_MODE", "false").lower() == "true"
        agent_logger = AgentLogger(enabled=dev_mode, log_dir="./logs/raw_data")
        
        log_data = {
            "schema": schema_info.model_dump(),
            "recommendations": response.model_dump()
        }
        agent_logger.log_raw_data("recommendation_log", log_data)

        return response
    
    async def get_database_schema(self, database_uid: str, table_uid: Optional[str] = None):
        """Get schema for a saved PostgreSQL database"""
        try:
            # Check Redis cache first
            cache_key = f"schema:{database_uid}:{table_uid}"
            cached_schema = self.redis_client.get_value(cache_key)
            if cached_schema:
                self.logger.info(f"AnalyticsService.get_database_schema - Schema retrieved from cache")
                return SchemaInfo(**cached_schema)

            # If not in cache, fetch from Neo4j
            schema = await self.repository.get_database_schema_from_neo4j(database_uid, table_uid)
            schema_info = convert_to_schema_info(schema)

            # Cache the result
            schema_dict = schema_info.model_dump()
            schema_json = json.dumps(schema_dict)
            self.redis_client.set_value(cache_key, schema_json, expiry=3600)  # Cache for 1 hour
            self.logger.info(f"AnalyticsService.get_database_schema - Schema cached")   

            return schema_info

        except Exception as e:
            self.logger.error(f"Error fetching schema from Neo4j: {e}")
            raise e

    async def create_excel_database(
        self,
        request: ExcelUploadRequestDTO,
        excel_file: UploadFile
    ) -> ExcelDatabaseDTO:
        """Create a new Excel database from uploaded file

        Args:
            request: The Excel upload request
            excel_file: The uploaded Excel file

        Returns:
            ExcelDatabaseDTO: The created Excel database
        """
        try:
            # Process the request through the schema service
            database = await self.schema_service.create_excel_database(
                request=request,
                excel_file=excel_file
            )
            
            # Convert database entity to DTO
            result = ExcelDatabaseDTO(
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
                    ExcelTableDTO(
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
                        storage_path=table.storage_path if hasattr(table, 'storage_path') else "",
                        sheet_name=table.name  # Excel sheet name is the same as table name
                    ) for table in database.tables.all()
                ]
            )
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error creating Excel database: {str(e)}")
            raise AnalyticsError(f"Error creating Excel database: {str(e)}")

        