from typing import List, Optional, Tuple, Dict, Any, Set, Union
from fastapi import UploadFile, HTTPException
import os
import logging
from datetime import datetime
import uuid

from app.analytics.api.dto import (
    DatabaseDTO,
    PostgresDatabaseDTO,
    TableDTO,
    CreatePostgresDatabaseRequestDTO,
    CSVDatabaseDTO,
    CreateCSVDatabaseRequestDTO,
    SchemaResponseDTO,
    RecommendationResponseDTO,
    DashboardResponseDTO,
    CreateDashboardRequestDTO,
    UpdateDashboardRequestDTO,
    DashboardListResponseDTO,
    DashboardAccessResponseDTO,
    DashboardAccessItemDTO,
    ShareDashboardRequestDTO,
    UpdatePermissionRequestDTO,
    AddDataframeRequestDTO,
    DataframeResponseDTO,
    ExcelUploadRequestDTO,
    ExcelDatabaseDTO,
    ChartTaskResponseDTO,
    ChartResponseDTO
)
from app.analytics.service.analytics_service import AnalyticsService
from app.analytics.service.dashboard_service import DashboardService
from app.analytics.service.chart_service import ChartService
from app.analytics.service.chart_queue_service import ChartQueueService
from app.analytics.service.dashboard_collaboration_service import DashboardCollaborationService
from app.analytics.service.postgres_service import PostgresService
from app.analytics.service.schema_service import SchemaService
from app.analytics.entity.chart import ChartTask, ChartStatus, ChartVisibility
from app.analytics.errors import (
    AnalyticsError,
    DatabaseNotFoundError,
    TableNotFoundError,
    UnauthorizedError,
    InvalidOperationError,
    DashboardError,
    DashboardNotFoundError,
    DashboardAccessDeniedError,
    DashboardCreationError,
    DashboardUpdateError,
    ChartNotFoundError,
    InsufficientPermissionError,
)
from pkg.log.logger import Logger
from app.analytics.api.converters import DTOConverter


class DashboardHandler:
    """Handler for dashboard operations"""
    
    def __init__(self, dashboard_service: DashboardService, logger: Logger, chart_service: ChartService):
        self.service = dashboard_service
        self.logger = logger
        self.chart_service = chart_service
    
    async def create_dashboard(self, request: CreateDashboardRequestDTO, requested_user_id: str,
                               org_id: str) -> DashboardResponseDTO:
        """Create a new dashboard"""
        try:
            dashboard = await self.service.create_dashboard(
                requested_user_id=requested_user_id,
                org_id = org_id,
                title=request.title,
                description=request.description,
                layout_config=request.layout_config,
                layouts=request.layouts
            )
            return DTOConverter.to_dashboard_dto(dashboard)
        except DashboardError as e:
            self.logger.error(f"Error creating dashboard: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error creating dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_dashboard(
        self, 
        dashboard_id: str, 
        requested_user_id: str,
        sync: Optional[bool] = None
    ) -> DashboardResponseDTO:
        """Get a dashboard by ID"""
        try:
            if sync:
                dashboard = await self.service.sync_dashboard(
                    dashboard_id=dashboard_id,
                    requested_user_id=requested_user_id
                )
            else:
                dashboard = await self.service.get_dashboard(
                        dashboard_id=dashboard_id,
                        requested_user_id=requested_user_id
                )
            return DTOConverter.to_dashboard_dto(dashboard)
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied to dashboard: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except Exception as e:
            self.logger.error(f"Error getting dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def list_dashboards(self, requested_user_id: str) -> List[DashboardResponseDTO]:
        """List dashboards accessible to the user"""
        try:
            dashboards = await self.service.list_dashboards(
                requested_user_id=requested_user_id
            )
            return [DTOConverter.to_dashboard_dto(dashboard) for dashboard in dashboards]
        except Exception as e:
            self.logger.error(f"Error listing dashboards: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_dashboard(self, dashboard_id: str, request: UpdateDashboardRequestDTO,
        requested_user_id: str) -> DashboardResponseDTO:
        """Update a dashboard"""
        try:
            dashboard = await self.service.update_dashboard(
                dashboard_id=dashboard_id,
                requested_user_id=requested_user_id,
                title=request.title,
                description=request.description,
                layout_config=request.layout_config,
                layouts=request.layouts
            )
            return DTOConverter.to_dashboard_dto(dashboard)
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied to dashboard: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except InsufficientPermissionError as e:
            self.logger.error(f"Insufficient permissions: {str(e)}")
            raise HTTPException(status_code=403, detail=str(e))
        except DashboardUpdateError as e:
            self.logger.error(f"Error updating dashboard: {e.message}")
            raise HTTPException(status_code=400, detail=e.message)
        except Exception as e:
            self.logger.error(f"Unexpected error updating dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def delete_dashboard(self, dashboard_id: str,requested_user_id: str) -> dict:
        """Delete a dashboard"""
        try:
            success = await self.service.delete_dashboard(
                dashboard_id=dashboard_id,
                requested_user_id=requested_user_id
            )
            if success:
                return {"message": "Dashboard deleted successfully"}
            else:
                return {"message": "Failed to delete dashboard"}
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied to dashboard: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except Exception as e:
            self.logger.error(f"Error deleting dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def restore_dashboard(
        self, 
        dashboard_id: str,
        user_id: str
    ) -> DashboardResponseDTO:
        """Restore a deleted dashboard"""
        try:
            dashboard = await self.service.restore_dashboard(
                dashboard_id=dashboard_id,
                user_id=user_id
            )
            if dashboard:
                return DTOConverter.to_dashboard_dto(dashboard)
            else:
                raise HTTPException(status_code=400, detail="Failed to restore dashboard")
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied to dashboard: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except Exception as e:
            self.logger.error(f"Error restoring dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def add_chart_to_dashboard(
        self,
        dashboard_id: str,
        chart_id: str,
        user_id: str,
        org_id: str
    ) -> DashboardResponseDTO:
        """Add a chart to a dashboard"""
        try:
            # First, get the chart to ensure it exists and can be accessed
            chart = await self.chart_service.get_chart(chart_id, user_id, org_id)
            
            # Then add the chart to the dashboard
            dashboard = await self.service.add_chart_to_dashboard(
                dashboard_id=dashboard_id,
                chart_id=chart_id,
                requested_user_id=user_id,
                org_id=org_id,
                chart_service=self.chart_service
            )
            
            # Create a DTO that includes the newly added chart
            dashboard_dto = DTOConverter.to_dashboard_dto(dashboard)
            
            # Ensure the newly added chart is included in the response
            # Check if the chart is already in the list
            chart_already_included = any(c["id"] == chart_id for c in dashboard_dto.charts)
            
            if not chart_already_included:
                # Add the chart to the response if it's not already included
                dashboard_dto.charts.append({
                    "id": chart.uid,
                    "title": chart.title,
                    "description": chart.description,
                    "chart_type": chart.chart_type,
                    "chart_schema": chart.chart_schema
                })
            
            return dashboard_dto
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied to dashboard: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except InsufficientPermissionError as e:
            self.logger.error(f"Insufficient permissions: {str(e)}")
            raise HTTPException(status_code=403, detail=str(e))
        except ChartNotFoundError as e:
            self.logger.error(f"Chart not found or not accessible: {str(e)}")
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            # Re-raise HTTPExceptions
            raise
        except Exception as e:
            self.logger.error(f"Error adding chart to dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def remove_chart_from_dashboard(
        self,
        dashboard_id: str,
        chart_id: str,
        requested_user_id: str,
            org_id: str
    ) -> DashboardResponseDTO:
        """Remove a chart from a dashboard"""
        try:
            # First, get the chart to ensure it exists and can be accessed
            chart = await self.chart_service.get_chart(chart_id, requested_user_id, org_id)
            
            # Then remove the chart from the dashboard
            dashboard = await self.service.remove_chart_from_dashboard(
                dashboard_id=dashboard_id,
                chart_id=chart_id,
                requested_user_id=requested_user_id,
                org_id=org_id,
                chart_service=self.chart_service
            )
            
            # Convert to DTO and return
            return DTOConverter.to_dashboard_dto(dashboard)
            
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied to dashboard: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except InsufficientPermissionError as e:
            self.logger.error(f"Insufficient permissions: {str(e)}")
            raise HTTPException(status_code=403, detail=str(e))
        except ChartNotFoundError as e:
            self.logger.error(f"Chart not found or not accessible: {str(e)}")
            raise HTTPException(status_code=404, detail=str(e))
        except HTTPException:
            # Re-raise HTTPExceptions
            raise
        except Exception as e:
            self.logger.error(f"Error removing chart from dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def add_dataframe_to_dashboard(
        self,
        dashboard_id: str,
        request: AddDataframeRequestDTO,
        requested_user_id: str
    ) -> DashboardResponseDTO:
        """Add a dataframe to a dashboard"""
        try:
            # Add the dataframe to the dashboard using the service
            dashboard, dataframe_entity = await self.service.add_dataframe_to_dashboard(
                dashboard_id=dashboard_id,
                requested_user_id=requested_user_id,
                content=request.content,
                columns=request.columns,
                metadata=request.metadata or "",
                message_id=request.message_id
            )
            
            # Convert the dashboard to a DTO
            return DTOConverter.to_dashboard_dto(dashboard)
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied to dashboard: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except InsufficientPermissionError as e:
            self.logger.error(f"Insufficient permissions: {str(e)}")
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.logger.error(f"Error adding dataframe to dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def remove_dataframe_from_dashboard(
        self,
        dashboard_id: str,
        dataframe_id: str,
        requested_user_id: str
    ) -> DashboardResponseDTO:
        """Remove a dataframe from a dashboard"""
        try:
            # Remove the dataframe from the dashboard using the service
            dashboard = await self.service.remove_dataframe_from_dashboard(
                dashboard_id=dashboard_id,
                dataframe_id=dataframe_id,
                requested_user_id=requested_user_id
            )
            
            # Convert the dashboard to a DTO
            return DTOConverter.to_dashboard_dto(dashboard)
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied to dashboard: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except InsufficientPermissionError as e:
            self.logger.error(f"Insufficient permissions: {str(e)}")
            raise HTTPException(status_code=403, detail=str(e))
        except Exception as e:
            self.logger.error(f"Error removing dataframe from dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


class AnalyticsHandler:
    """Handler for analytics operations"""
    
    def __init__(self, analytics_service: AnalyticsService, logger: Logger, 
                 chart_queue_service: ChartQueueService, chart_service: ChartService):
        self.service = analytics_service
        self.logger = logger
        self.chart_queue_service = chart_queue_service
        self.chart_service = chart_service

    async def list_databases(self, user_id: str) -> List[DatabaseDTO]:
        """List all mapped databases"""
        try:
            return await self.service.list_databases(user_id)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error listing databases: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def list_postgres_databases(self) -> List[PostgresDatabaseDTO]:
        """List all PostgreSQL databases"""
        try:
            return await self.service.list_postgres_databases()
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error listing PostgreSQL databases: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_database_by_uid(self, database_uid: str) -> DatabaseDTO:
        """Get database by UID"""
        try:
            return await self.service.get_database_by_uid(database_uid)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error getting database: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_table_by_uid(self, database_uid: str, table_uid: str) -> TableDTO:
        """Get table by UID"""
        try:
            return await self.service.get_table_by_uid(database_uid, table_uid)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error getting table: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_postgres_database(self, request: CreatePostgresDatabaseRequestDTO) -> PostgresDatabaseDTO:
        """Create/Connect to a PostgreSQL database and map its schema"""
        try:
            return await self.service.create_postgres_database(request)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error creating PostgreSQL database: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_csv_database(
        self,
        request: CreateCSVDatabaseRequestDTO,
        csv_files: List[UploadFile]
    ) -> CSVDatabaseDTO:
        """Create a new CSV database from uploaded files"""
        try:
            return await self.service.create_csv_database(request, csv_files)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error creating CSV database: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def add_csv_files(
        self,
        database_uid: str,
        user_id: str,
        csv_files: List[UploadFile]
    ) -> CSVDatabaseDTO:
        """Add more CSV files to an existing database"""
        try:
            return await self.service.add_csv_files(database_uid, user_id, csv_files)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error adding CSV files: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_excel_database(self, request: ExcelUploadRequestDTO, excel_file: UploadFile) -> ExcelDatabaseDTO:
        """Create a new Excel database from uploaded file"""
        try:
            return await self.service.create_excel_database(request, excel_file)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error creating Excel database: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def map_postgres_schema(self, database_name: Optional[str] = None, database_uid: Optional[str] = None, user_id: Optional[str] = None) -> SchemaResponseDTO:
        """Map PostgreSQL database schema"""
        try:
            # Only pass user_id if it's not None to avoid type error
            kwargs = {}
            if database_name is not None:
                kwargs['database_name'] = database_name
            if database_uid is not None:
                kwargs['database_uid'] = database_uid
            if user_id is not None:
                kwargs['user_id'] = user_id
            
            return await self.service.map_postgres_schema(**kwargs)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error mapping PostgreSQL schema: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def soft_delete_table(self, database_uid: str, table_uid: str, user_id: str) -> None:
        """Soft delete a table"""
        try:
            await self.service.soft_delete_table(database_uid, table_uid, user_id)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error soft deleting table: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def restore_table(self, database_uid: str, table_uid: str, user_id: str) -> None:
        """Restore a soft-deleted table"""
        try:
            await self.service.restore_table(database_uid, table_uid, user_id)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error restoring table: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def soft_delete_database(self, database_uid: str, user_id: str) -> None:
        """Soft delete a database and all its tables"""
        try:
            await self.service.soft_delete_database(database_uid, user_id)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error soft deleting database: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def restore_database(self, database_uid: str, user_id: str, restore_tables: bool = True) -> None:
        """Restore a soft-deleted database"""
        try:
            await self.service.restore_database(database_uid, user_id, restore_tables)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error restoring database: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_deleted_tables(self, database_uid: str, user_id: str) -> List[TableDTO]:
        """Get all soft-deleted tables in a database"""
        try:
            return await self.service.get_deleted_tables(database_uid, user_id)
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error getting deleted tables: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def get_recommendations(
        self,
        database_uid: str,
        table_uid: Optional[str] = None,
        count: int = 5,
        user_question: Optional[str] = None,
    ) -> RecommendationResponseDTO:
        """Get query recommendations based on database schema"""
        try:
            # Simply pass the llm_client to the service
            return await self.service.get_recommendations(
                database_uid=database_uid,
                table_uid=table_uid,
                count=count,
                user_question=user_question,
            )
        except AnalyticsError as e:
            raise e.to_http_exception()
        except Exception as e:
            self.logger.error(f"Error getting recommendations: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))

    async def create_chart_task(
        self,
        message_id: uuid.UUID,
        user_id: str,
        org_id: str,
        visibility: str,
        force_create: bool,
        adjustment_query: Optional[str] = None
    ) -> ChartTask:
        """Create a chart generation task and queue it"""
        try:
            self.logger.info(f"Creating chart task for message: {message_id}")
            # Create task
            task = ChartTask(
                task_id=str(uuid.uuid4()),
                message_id=message_id,
                user_id=user_id,
                org_id=org_id,
                status=ChartStatus.PENDING,
                progress=0,
                created_at=datetime.utcnow(),
                visibility=ChartVisibility(visibility),
                force_create=force_create,
                adjustment_query=adjustment_query,
                current_step="queued"
            )

            self.logger.info(f"Created chart task: {task}")
            
            # Queue the task
            success = await self.chart_queue_service.enqueue_chart_task(task)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to queue chart task")
            
            return task
            
        except Exception as e:
            self.logger.error(f"Error creating chart task: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_chart_task_status(self, task_id: str, user_id: str) -> Optional[ChartTaskResponseDTO]:
        """Get chart task status"""
        try:
            # Get raw task data without reconstruction to avoid corruption
            task_data = await self.chart_queue_service.get_task_data(task_id)
            if not task_data:
                return None
            
            # Verify user owns the task
            if task_data.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Get current status
            status_data = await self.chart_queue_service.get_task_status(task_id)
            if status_data:
                # Parse datetime fields safely
                from datetime import datetime
                created_at = None
                started_at = None
                completed_at = None
                estimated_completion = None
                
                try:
                    if task_data.get("created_at"):
                        created_at = datetime.fromisoformat(task_data["created_at"]) if isinstance(task_data["created_at"], str) else task_data["created_at"]
                    if task_data.get("started_at"):
                        started_at = datetime.fromisoformat(task_data["started_at"]) if isinstance(task_data["started_at"], str) else task_data["started_at"]
                    if task_data.get("completed_at"):
                        completed_at = datetime.fromisoformat(task_data["completed_at"]) if isinstance(task_data["completed_at"], str) else task_data["completed_at"]
                    if task_data.get("estimated_completion"):
                        estimated_completion = datetime.fromisoformat(task_data["estimated_completion"]) if isinstance(task_data["estimated_completion"], str) else task_data["estimated_completion"]
                except ValueError as e:
                    self.logger.error(f"Error parsing datetime fields: {str(e)}")
                
                return ChartTaskResponseDTO(
                    task_id=task_data["task_id"],
                    message_id=task_data["message_id"],
                    status=ChartStatus(status_data["status"]),
                    progress=status_data["progress"],
                    current_step=status_data["current_step"],
                    error_message=status_data.get("error_message"),
                    created_at=created_at or datetime.now(),
                    started_at=started_at,
                    completed_at=completed_at,
                    estimated_completion=estimated_completion,
                    message=self._get_status_message(status_data["status"])
                )
            
            return None
            
        except HTTPException:
            # Re-raise HTTPExceptions to preserve their status codes
            raise
        except Exception as e:
            self.logger.error(f"Error getting chart task status: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_chart_by_task_id(self, task_id: str, user_id: str) -> Optional[ChartResponseDTO]:
        """Get completed chart by task ID"""
        try:
            # Get raw task data without reconstruction to avoid corruption
            task_data = await self.chart_queue_service.get_task_data(task_id)
            if not task_data:
                self.logger.error(f"Task data not found for task_id: {task_id}")
                return None
            
            # Verify user owns the task
            if task_data.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Check if task is completed using raw data
            task_status = task_data.get("status")
            chart_id = task_data.get("chart_id")
            
            self.logger.info(f"Task {task_id} raw data - status: {task_status}, chart_id: {chart_id}")
            
            if task_status != "COMPLETED":
                self.logger.error(f"Task {task_id} not completed, status: {task_status}")
                return None
            
            if not chart_id:
                self.logger.error(f"Task {task_id} completed but no chart_id found")
                return None
            
            self.logger.info(f"Task {task_id} completed with chart_id: {chart_id}")
            
            # Get the chart
            chart = await self.chart_service.get_chart(
                chart_id=chart_id,
                user_id=user_id,
                org_id=task_data.get("org_id") or ""
            )
            
            if not chart:
                self.logger.error(f"Chart not found for chart_id: {chart_id}")
                return None
            
            return ChartResponseDTO.from_entity(chart)
            
        except HTTPException:
            # Re-raise HTTPExceptions to preserve their status codes
            raise
        except Exception as e:
            self.logger.error(f"Error getting chart by task ID: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def cancel_chart_task(self, task_id: str, user_id: str) -> bool:
        """Cancel a chart generation task"""
        try:
            # Get task data
            task = await self.chart_queue_service.get_task_data(task_id)
            if not task:
                return False
            
            # Verify user owns the task
            if task.get("user_id") != user_id:
                raise HTTPException(status_code=403, detail="Access denied")
            
            # Cancel the task
            return await self.chart_queue_service.cancel_task(task_id)
            
        except HTTPException:
            # Re-raise HTTPExceptions to preserve their status codes
            raise
        except Exception as e:
            self.logger.error(f"Error cancelling chart task: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    def _get_status_message(self, status: str) -> str:
        """Get human-readable status message"""
        messages = {
            "PENDING": "Chart generation queued",
            "PROCESSING": "Chart generation in progress",
            "COMPLETED": "Chart generation completed",
            "FAILED": "Chart generation failed",
            "CANCELLED": "Chart generation cancelled"
        }
        return messages.get(status, "Unknown status")
    
    async def get_active_chart_tasks_by_message(self, message_id: str, user_id: str) -> List[ChartTaskResponseDTO]:
        """Get active chart tasks for a specific message"""
        try:
            active_tasks = await self.chart_queue_service.get_active_tasks_by_message_id(
                message_id=message_id,
                user_id=user_id
            )
            
            result = []
            for task_data in active_tasks:
                # Parse datetime fields
                created_at = None
                started_at = None
                
                try:
                    if task_data.get("created_at"):
                        created_at = datetime.fromisoformat(task_data["created_at"]) if isinstance(task_data["created_at"], str) else task_data["created_at"]
                    if task_data.get("started_at"):
                        started_at = datetime.fromisoformat(task_data["started_at"]) if isinstance(task_data["started_at"], str) else task_data["started_at"]
                except ValueError as e:
                    self.logger.error(f"Error parsing datetime fields: {str(e)}")
                
                result.append(ChartTaskResponseDTO(
                    task_id=task_data["task_id"],
                    message_id=task_data["message_id"],
                    status=ChartStatus(task_data["status"]),
                    progress=task_data["progress"],
                    current_step=task_data["current_step"],
                    error_message=None,
                    created_at=created_at or datetime.now(),
                    started_at=started_at,
                    completed_at=None,
                    estimated_completion=None,
                    message=self._get_status_message(task_data["status"])
                ))
            
            return result
            
        except Exception as e:
            self.logger.error(f"Error getting active chart tasks by message: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))


class DashboardCollaborationHandler:
    """Handler for dashboard collaboration operations"""
    
    def __init__(self, collaboration_service: DashboardCollaborationService, logger: Logger):
        self.service = collaboration_service
        self.logger = logger
    
    async def share_dashboard(
        self, 
        dashboard_id: str,
        request: ShareDashboardRequestDTO, 
        requested_user_id: str
    ) -> DashboardResponseDTO:
        """Share a dashboard with users"""
        try:
            # Convert DTO to service format
            user_access_list = [
                {"user_id": item.user_id, "permission": item.permission}
                for item in request.users
            ]
            
            dashboard = await self.service.share_with_users(
                dashboard_id=dashboard_id,
                requested_user_id=requested_user_id,
                user_access_list=user_access_list
            )
            return DTOConverter.to_dashboard_dto(dashboard)
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except InsufficientPermissionError as e:
            self.logger.error(f"Insufficient permissions: {str(e)}")
            raise HTTPException(status_code=403, detail=str(e))
        except DashboardError as e:
            self.logger.error(f"Error sharing dashboard: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error sharing dashboard: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def remove_user_access(
        self, 
        dashboard_id: str,
        requested_user_id: str,
        user_id: str
    ) -> DashboardResponseDTO:
        """Remove a user's access to a dashboard"""
        try:
            dashboard = await self.service.remove_user_access(
                dashboard_id=dashboard_id,
                requested_user_id=requested_user_id,
                user_id=user_id
            )
            return DTOConverter.to_dashboard_dto(dashboard)
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except InsufficientPermissionError as e:
            self.logger.error(f"Insufficient permissions: {str(e)}")
            raise HTTPException(status_code=403, detail=str(e))
        except DashboardError as e:
            self.logger.error(f"Error removing user access: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error removing user access: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def update_user_permission(
        self, 
        dashboard_id: str,
        user_id: str,
        request: UpdatePermissionRequestDTO,
        requested_user_id: str
    ) -> DashboardResponseDTO:
        """Update a user's permission level for a dashboard"""
        try:
            dashboard = await self.service.update_user_permission(
                dashboard_id=dashboard_id,
                requested_user_id=requested_user_id,
                user_id=user_id,
                permission=request.permission
            )
            return DTOConverter.to_dashboard_dto(dashboard)
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except InsufficientPermissionError as e:
            self.logger.error(f"Insufficient permissions: {str(e)}")
            raise HTTPException(status_code=403, detail=str(e))
        except DashboardError as e:
            self.logger.error(f"Error updating user permission: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error updating user permission: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
    
    async def get_dashboard_access(
        self, 
        dashboard_id: str,
        user_id: str
    ) -> DashboardAccessResponseDTO:
        """Get access information for a dashboard"""
        try:
            access_list = await self.service.get_dashboard_access(
                dashboard_id=dashboard_id,
                requested_user_id=user_id
            )
            
            # Convert to DTO format
            user_access_items = [
                DashboardAccessItemDTO(user_id=item["user_id"], permission=item["permission"])
                for item in access_list
            ]
            
            return DashboardAccessResponseDTO(
                dashboard_id=dashboard_id,
                users=user_access_items
            )
        except DashboardNotFoundError as e:
            self.logger.error(f"Dashboard not found: {e.message}")
            raise HTTPException(status_code=404, detail=e.message)
        except DashboardAccessDeniedError as e:
            self.logger.error(f"Access denied: {e.message}")
            raise HTTPException(status_code=403, detail=e.message)
        except DashboardError as e:
            self.logger.error(f"Error getting dashboard access: {str(e)}")
            raise HTTPException(status_code=400, detail=str(e))
        except Exception as e:
            self.logger.error(f"Unexpected error getting dashboard access: {str(e)}")
            raise HTTPException(status_code=500, detail=str(e))
