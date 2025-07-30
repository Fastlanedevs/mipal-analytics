from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any, Union, TYPE_CHECKING

from pydantic import BaseModel, Field, validator

from app.analytics.entity.chart import ChartType, ChartVisibility, ChartAdjustmentOption, ChartStatus

if TYPE_CHECKING:
    from app.analytics.entity.chart import Chart
from uuid import UUID

# Dashboard-related DTOs
class DashboardLayoutDTO(BaseModel):
    """Layout information for a chart in a dashboard"""
    chart_id: str
    position_x: int
    position_y: int
    width: int
    height: int
    config: Optional[Dict[str, Any]] = None


class CreateDashboardRequestDTO(BaseModel):
    """Request DTO for dashboard creation"""
    title: str = Field(..., description="Dashboard title")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout_config: Optional[Dict[str, Any]] = Field(None, description="Overall dashboard layout configuration")
    layouts: Optional[Dict[str, Any]] = Field(None, description="Chart layouts")


class UpdateDashboardRequestDTO(BaseModel):
    """Request DTO for updating dashboard information"""
    title: Optional[str] = Field(None, description="Dashboard title")
    description: Optional[str] = Field(None, description="Dashboard description")
    layout_config: Optional[Dict[str, Any]] = Field(None, description="Overall dashboard layout configuration")
    layouts: Optional[Dict[str, Any]] = Field(None, description="Chart layouts")

# Dataframe-related DTOs
class DataframeResponseDTO(BaseModel):
    """Response DTO for dataframe information"""
    dataframe_id: str
    content: str  # JSON string of dataframe content
    columns: str  # JSON string of column definitions
    metadata: Optional[str] = None
    user_id: str
    message_id: Optional[str] = None  # ID of the message that triggered this dataframe creation
    created_at: datetime
    updated_at: datetime


class AddDataframeRequestDTO(BaseModel):
    """Request DTO for adding a dataframe to a dashboard"""
    content: str = Field(..., description="JSON string containing dataframe content")
    columns: str = Field(..., description="JSON string defining column structure")
    metadata: Optional[str] = Field("{}", description="Additional metadata as JSON string")
    message_id: Optional[str] = Field(None, description="ID of the message that triggered this dataframe creation")

class DashboardResponseDTO(BaseModel):
    """Response DTO for dashboard information"""
    dashboard_id: str
    title: str
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None
    layouts: Optional[Dict[str, Any]] = None
    charts: List[Dict[str, Any]] = Field(default_factory=list,
                                         description="List of charts associated with this dashboard")
    dataframes: List[DataframeResponseDTO] = Field(default_factory=list,
                                               description="List of dataframes associated with this dashboard")
    user_id: str
    org_id: Optional[str] = None
    created_at: datetime
    updated_at: datetime


class DashboardListResponseDTO(BaseModel):
    """Response DTO for listing dashboards"""
    items: List[DashboardResponseDTO]
    total: int


# Dashboard Collaboration DTOs
class DashboardAccessItemDTO(BaseModel):
    """DTO for a user's dashboard access information"""
    user_id: str = Field(..., description="ID of the user")
    permission: str = Field(..., description="Permission level ('view' or 'edit')")

    @validator('permission')
    def validate_permission(cls, v):
        if v not in ["view", "edit"]:
            raise ValueError("Permission must be 'view' or 'edit'")
        return v


class ShareDashboardRequestDTO(BaseModel):
    """Request DTO for sharing a dashboard with users"""
    users: List[DashboardAccessItemDTO] = Field(..., description="List of users to share the dashboard with")


class UpdatePermissionRequestDTO(BaseModel):
    """Request DTO for updating a user's permission level"""
    permission: str = Field(..., description="New permission level ('view' or 'edit')")

    @validator('permission')
    def validate_permission(cls, v):
        if v not in ["view", "edit"]:
            raise ValueError("Permission must be 'view' or 'edit'")
        return v


class DashboardAccessResponseDTO(BaseModel):
    """Response DTO for dashboard access information"""
    dashboard_id: str
    users: List[DashboardAccessItemDTO] = Field(default_factory=list,
                                                description="List of users with access to the dashboard")


# Base Models
class ColumnDTO(BaseModel):
    """Column information DTO"""
    uid: str
    name: str
    data_type: str
    description: Optional[str] = None
    is_primary_key: bool = False
    is_nullable: bool = True
    default: Optional[str] = None
    stats: Dict[str, Any] = {}


class TableDTO(BaseModel):
    """Table information DTO"""
    uid: str
    name: str
    schema_name: str
    description: Optional[str] = None
    columns: List[ColumnDTO]
    row_count: int = 0
    last_updated: Optional[str] = None


class DatabaseDTO(BaseModel):
    """Base database information DTO"""
    uid: str
    name: str
    type: str
    description: Optional[str] = None
    tables: Optional[List[TableDTO]] = None
    user_id: str
    integration_id: str
    is_active: bool = True
    created_at: str
    updated_at: str


class RelationshipDTO(BaseModel):
    """Relationship information DTO"""
    type: str
    from_table: str
    to_table: str
    from_column: str
    to_column: str


# PostgreSQL DTOs
class PostgresColumnDTO(ColumnDTO):
    """PostgreSQL column information DTO"""
    character_length: Optional[int] = None
    numeric_precision: Optional[int] = None
    numeric_scale: Optional[int] = None
    is_foreign_key: bool = False
    references: Optional[str] = None  # Format: "table_name.column_name"


class PostgresTableDTO(TableDTO):
    """PostgreSQL table information DTO"""
    columns: List[PostgresColumnDTO]
    total_size: Optional[str] = None
    table_size: Optional[str] = None
    index_size: Optional[str] = None
    row_estimate: Optional[int] = None
    has_indices: bool = False
    primary_key: Optional[str] = None
    foreign_keys: List[RelationshipDTO] = []


class PostgresSchemaDTO(BaseModel):
    """PostgreSQL schema information DTO"""
    name: str
    tables: List[str]
    owner: Optional[str] = None
    privileges: Optional[List[str]] = None


class PostgresDatabaseDTO(DatabaseDTO):
    """PostgreSQL database information DTO"""
    host: str
    port: int
    user: str
    schemas: Optional[List[PostgresSchemaDTO]] = None
    tables: List[PostgresTableDTO] = []  # Override tables type


class PostgresSyncRequestDTO(BaseModel):
    """Request DTO for syncing PostgreSQL database schema"""
    database_name: str = Field(..., description="Name of the PostgreSQL database to map")
    host: str = Field(default="localhost", description="Database host")
    port: int = Field(default=5432, description="Database port")
    user: str = Field(..., description="Database user")
    password: str = Field(..., description="Database password")


class CreatePostgresDatabaseRequestDTO(BaseModel):
    """Request DTO for creating/connecting to a PostgreSQL database"""
    database_name: str
    host: str
    port: int
    user: str
    password: str
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = None
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None  # Made optional since it will be set from token
    integration_id: str

    def set_user_id(self, user_id: str) -> None:
        """Set the user_id from the token"""
        self.user_id = user_id


# CSV DTOs
class CSVTableDTO(TableDTO):
    """CSV table information DTO"""
    storage_url: Optional[str] = None
    storage_bucket: str = ""
    storage_path: str = ""


class CSVDatabaseDTO(DatabaseDTO):
    """CSV database information DTO"""
    tables: List[CSVTableDTO] = []


class CreateCSVDatabaseRequestDTO(BaseModel):
    """Request DTO for creating/connecting to a CSV database"""
    database_name: str
    description: str | None = None
    settings: dict = {}
    credentials: dict = {
        "host": str,
        "port": str,
        "user": str,
        "password": str
    }
    metadata: Optional[Dict[str, Any]] = None
    user_id: Optional[str] = None  # Made optional since it will be set from token

    def set_user_id(self, user_id: str) -> None:
        """Set the user_id from the token"""
        self.user_id = user_id


class CSVUploadRequestDTO(BaseModel):
    """Request DTO for uploading CSV files"""
    database_name: str = Field(..., description="Name of the CSV database")
    description: Optional[str] = None
    settings: Optional[Dict[str, Any]] = Field(default={}, description="Additional settings for CSV processing")
    metadata: Optional[Dict[str, Any]] = Field(default={}, description="Additional metadata")
    user_id: Optional[str] = None  # Will be set from token


class CSVFileInfo(BaseModel):
    """File information for CSV uploads"""
    path: str
    table_name: Optional[str] = None
    bucket: Optional[str] = None
    url: Optional[str] = None


class CSVFileUploadResponse(BaseModel):
    """Response DTO for CSV file upload"""
    file_name: str
    table_name: str
    row_count: int
    column_count: int
    storage_url: Optional[str] = None
    column_stats: Optional[Dict[str, Dict[str, Any]]] = None

# Schema DTOs
class SchemaResponseDTO(BaseModel):
    """Response DTO for schema operations"""
    message: str
    schema_name: Optional[str] = None
    error: Optional[str] = None

# Excel DTOs
class ExcelTableDTO(TableDTO):
    """Excel table information DTO"""
    storage_url: Optional[str] = None
    storage_bucket: str = ""
    storage_path: str = ""
    sheet_name: str = ""


class ExcelDatabaseDTO(DatabaseDTO):
    """Excel database information DTO"""
    tables: List[ExcelTableDTO] = []


class ExcelUploadRequestDTO(BaseModel):
    """Request DTO for uploading Excel files"""
    database_name: str = Field(..., description="Name of the Excel database")
    description: Optional[str] = Field(None, description="Database description")
    user_id: Optional[str] = None  # Will be set from token

    def set_user_id(self, user_id: str) -> None:
        """Set the user_id from the token"""
        self.user_id = user_id

# Chart DTOs
class CreateChartRequestDTO(BaseModel):
    """Request DTO for chart creation"""
    message_id: UUID = Field(..., description="ID of the message to create chart from")
    visibility: ChartVisibility = Field(ChartVisibility.PRIVATE, description="Chart visibility setting")
    force_create: bool = Field(False, description="If True, creates a new chart even if one exists for the message")
    adjustment_query: Optional[str] = Field(None,
                                            description="Optional query for requesting an alternate chart visualization")


class ChartTaskResponseDTO(BaseModel):
    """Response DTO for chart generation task"""
    task_id: str = Field(..., description="Unique task ID for tracking")
    message_id: str = Field(..., description="ID of the message this task is for")
    status: ChartStatus = Field(..., description="Current task status")
    progress: int = Field(..., description="Progress percentage (0-100)")
    current_step: str = Field(..., description="Current processing step")
    error_message: Optional[str] = Field(None, description="Error message if failed")
    created_at: datetime = Field(..., description="Task creation timestamp")
    started_at: Optional[datetime] = Field(None, description="Task start timestamp")
    completed_at: Optional[datetime] = Field(None, description="Task completion timestamp")
    estimated_completion: Optional[datetime] = Field(None, description="Estimated completion time")
    message: str = Field(..., description="Human-readable status message")


class ChartResponseDTO(BaseModel):
    """Response DTO for chart data"""
    id: str
    title: str
    description: Optional[str] = None
    chart_type: ChartType
    chart_schema: Dict[str, Any]
    chart_data: List[Dict[str, Any]]
    message_id: UUID
    visibility: ChartVisibility
    created_at: datetime
    updated_at: datetime
    last_refreshed_at: datetime
    available_adjustments: Optional[Dict[str, Any]] = None
    alternative_visualizations: Optional[List[Dict[str, Any]]] = None
    alternative_visualization_queries: Optional[List[Dict[str, Any]]] = None
    # New fields for async processing
    status: ChartStatus = ChartStatus.COMPLETED
    task_id: Optional[str] = None
    progress: int = 100
    error_message: Optional[str] = None

    @staticmethod
    def from_entity(chart: 'Chart') -> 'ChartResponseDTO':
        """Convert a Chart entity to ChartResponseDTO"""
        import json
        import logging

        logger = logging.getLogger(__name__)

        # Properly handle chart data
        chart_data = []
        if chart.chart_data:
            if isinstance(chart.chart_data, str):
                try:
                    chart_data = json.loads(chart.chart_data)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse chart_data as JSON for chart {chart.uid}")
                    chart_data = []
            elif isinstance(chart.chart_data, list):
                chart_data = chart.chart_data
            else:
                logger.error(f"Unexpected chart_data type: {type(chart.chart_data)}")

        # Properly handle chart schema
        chart_schema = {}
        if chart.chart_schema:
            if isinstance(chart.chart_schema, str):
                try:
                    chart_schema = json.loads(chart.chart_schema)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse chart_schema as JSON for chart {chart.uid}")
                    chart_schema = {}
            elif isinstance(chart.chart_schema, dict):
                chart_schema = chart.chart_schema
            else:
                logger.error(f"Unexpected chart_schema type: {type(chart.chart_schema)}")

        # Handle available_field_mappings
        available_adjustments = None
        if hasattr(chart, 'available_field_mappings') and chart.available_field_mappings:
            if isinstance(chart.available_field_mappings, str):
                try:
                    available_adjustments = json.loads(chart.available_field_mappings)
                except json.JSONDecodeError:
                    logger.error(f"Failed to parse available_field_mappings as JSON for chart {chart.uid}")
                    available_adjustments = None
            elif isinstance(chart.available_field_mappings, dict):
                available_adjustments = chart.available_field_mappings

        # Handle alternative visualizations
        alternative_visualizations = None
        if hasattr(chart, 'alternative_visualizations'):
            logger.info(
                f"Chart entity has alternative_visualizations attribute: {chart.alternative_visualizations is not None}")
            if chart.alternative_visualizations:
                if isinstance(chart.alternative_visualizations, str):
                    try:
                        alternative_visualizations = json.loads(chart.alternative_visualizations)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse alternative_visualizations as JSON for chart {chart.uid}")
                        alternative_visualizations = None
                elif isinstance(chart.alternative_visualizations, list):
                    alternative_visualizations = chart.alternative_visualizations
                else:
                    logger.error(f"Unexpected alternative_visualizations type: {type(chart.alternative_visualizations)}")

        # Handle alternative visualization queries
        alternative_visualization_queries = None
        if hasattr(chart, 'alternative_visualization_queries'):
            logger.info(
                f"Chart entity has alternative_visualization_queries attribute: {chart.alternative_visualization_queries is not None}")
            if chart.alternative_visualization_queries:
                if isinstance(chart.alternative_visualization_queries, str):
                    try:
                        alternative_visualization_queries = json.loads(chart.alternative_visualization_queries)
                    except json.JSONDecodeError:
                        logger.error(f"Failed to parse alternative_visualization_queries as JSON for chart {chart.uid}")
                        alternative_visualization_queries = None
                elif isinstance(chart.alternative_visualization_queries, list):
                    alternative_visualization_queries = chart.alternative_visualization_queries
                else:
                    logger.error(f"Unexpected alternative_visualization_queries type: {type(chart.alternative_visualization_queries)}")

        # Handle chart_type conversion with error handling
        try:
            chart_type = ChartType(chart.chart_type)
        except ValueError:
            logger.error(f"Invalid chart_type '{chart.chart_type}' for chart {chart.uid}, using EMPTY")
            chart_type = ChartType.EMPTY

        return ChartResponseDTO(
            id=chart.uid,
            title=chart.title,
            description=chart.description,
            chart_type=chart_type,
            chart_schema=chart_schema,
            chart_data=chart_data,
            message_id=chart.message_id,
            visibility=chart.visibility,
            created_at=chart.created_at,
            updated_at=chart.updated_at,
            last_refreshed_at=chart.last_refreshed_at,
            available_adjustments=available_adjustments,
            alternative_visualizations=alternative_visualizations,
            alternative_visualization_queries=alternative_visualization_queries,
            status=getattr(chart, 'status', ChartStatus.COMPLETED),
            task_id=getattr(chart, 'task_id', None),
            progress=getattr(chart, 'progress', 100),
            error_message=getattr(chart, 'error_message', None)
        )


class MessageChartsResponseDTO(BaseModel):
    """Response DTO for charts and active tasks for a message"""
    charts: List[ChartResponseDTO] = Field(..., description="Completed charts")
    active_tasks: List[ChartTaskResponseDTO] = Field(..., description="Active chart generation tasks")
    has_active_tasks: bool = Field(..., description="Whether there are active tasks")


class UpdateChartRequestDTO(BaseModel):
    """Request DTO for updating chart metadata"""
    title: Optional[str] = None
    description: Optional[str] = None
    visibility: Optional[ChartVisibility] = None


class AdjustChartRequestDTO(BaseModel):
    """Request DTO for chart adjustment"""
    adjustment_options: ChartAdjustmentOption


class AdjustChartResponseDTO(ChartResponseDTO):
    """Response DTO for chart adjustment with status information"""
    adjustment_status: bool = Field(default=False, description="Whether the adjustment was successful")
    adjustment_message: str = Field(default="", description="Message explaining the adjustment result")

    @staticmethod
    def from_entity_with_status(chart: 'Chart', status: bool, message: str) -> 'AdjustChartResponseDTO':
        """Create a new AdjustChartResponseDTO from a Chart entity with status information"""
        base_dto = ChartResponseDTO.from_entity(chart)
        return AdjustChartResponseDTO(
            **base_dto.dict(),
            adjustment_status=status,
            adjustment_message=message
        )


class ChartDimensionsDTO(BaseModel):
    """Request DTO for updating chart dimensions"""
    width: int = Field(..., description="Chart width in pixels", gt=0)
    height: int = Field(..., description="Chart height in pixels", gt=0)


class ChartHistoryResponseDTO(BaseModel):
    """Response DTO for chart history"""
    id: str
    chart_id: str
    chart_type: ChartType
    chart_schema: Dict[str, Any]
    chart_data: List[Dict[str, Any]]
    modified_by: str
    created_at: datetime


class ChartsListResponseDTO(BaseModel):
    """Response DTO for listing charts"""
    items: List[ChartResponseDTO]
    total: int


class ChartHistoryListResponseDTO(BaseModel):
    """Response DTO for chart history list"""
    items: List[ChartHistoryResponseDTO]
    total: int


class RecommendationItemDTO(BaseModel):
    """DTO for a single recommendation item"""
    title: str
    explanation: str
    question: str
    category: str


class RecommendationResponseDTO(BaseModel):
    """Response DTO for recommendation endpoint"""
    recommendations: List[RecommendationItemDTO]


class RecommendationRequestDTO(BaseModel):
    """Request DTO for recommendation endpoint"""
    database_uid: str
    table_uid: Optional[str] = None
    count: int = 5
    user_question: Optional[str] = None


# Add new request model for database restore
class RestoreDatabaseRequest(BaseModel):
    restore_tables: bool = True


class AddChartToDashboardRequestDTO(BaseModel):
    """Request DTO for adding a chart to a dashboard"""
    chart_id: str
    position_x: int = 0
    position_y: int = 0
    width: int = 4
    height: int = 4
    config: Optional[Dict[str, Any]] = None
