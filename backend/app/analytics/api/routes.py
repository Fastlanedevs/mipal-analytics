from typing import List, Annotated, Optional, Dict, Any, AsyncGenerator
from uuid import UUID
from fastapi import APIRouter, HTTPException, Depends, UploadFile, File, Form, Request, Query, Path, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse, StreamingResponse
from pydantic import ValidationError, BaseModel
import json
import asyncio
from datetime import datetime

from app.analytics.api.dto import (
    DatabaseDTO,
    PostgresDatabaseDTO,
    TableDTO,
    CreatePostgresDatabaseRequestDTO,
    CSVDatabaseDTO,
    CreateCSVDatabaseRequestDTO,
    SchemaResponseDTO,
    CreateChartRequestDTO,
    ChartResponseDTO,
    UpdateChartRequestDTO,
    AdjustChartRequestDTO,
    ChartHistoryResponseDTO,
    ChartsListResponseDTO,
    ChartHistoryListResponseDTO,
    RecommendationRequestDTO,
    RecommendationResponseDTO,
    AdjustChartResponseDTO,
    ChartDimensionsDTO,
    # Dashboard DTOs
    DashboardResponseDTO,
    CreateDashboardRequestDTO,
    UpdateDashboardRequestDTO,
    DashboardListResponseDTO,
    AddChartToDashboardRequestDTO,
    # Dashboard Collaboration DTOs
    ShareDashboardRequestDTO,
    UpdatePermissionRequestDTO,
    DashboardAccessResponseDTO,
    RestoreDatabaseRequest,
    # Dataframe DTOs
    AddDataframeRequestDTO,
    DataframeResponseDTO,
    ExcelDatabaseDTO,
    ExcelUploadRequestDTO,
    ChartTaskResponseDTO,
    MessageChartsResponseDTO
)

from app.middleware import get_token_detail
from app.analytics.api.dependencies import (AnalyticsHandlerDep, DashboardHandlerDep,
                                            DashboardCollaborationHandlerDep, ChartServiceDep, ChartQueueServiceDep)
from app.analytics.service.chart_queue_service import ChartQueueService

from app.analytics.errors import (
    ChartNotFoundError,
    ChartAccessDeniedError,
    MessageNotFoundError,
    ChartCreationError,
    ChartUpdateError,
    ChartRefreshError,
    InvalidChartDataError,
    AnalyticsError,
    DashboardNotFoundError,
    DashboardAccessDeniedError,
    DashboardCreationError,
    DashboardUpdateError,
    InsufficientPermissionError
)

from app.middleware.auth import TokenData

analytics_router = APIRouter(prefix="/analytics", tags=["Analytics"])


@analytics_router.get("/databases", response_model=List[DatabaseDTO])
async def list_databases(
        analytics_handler: AnalyticsHandlerDep,
        token_detail: Annotated[TokenData, Depends(get_token_detail)]) -> List[DatabaseDTO]:
    """List all mapped databases"""
    return await analytics_handler.list_databases(token_detail.user_id)


@analytics_router.get("/postgres/databases", response_model=List[PostgresDatabaseDTO])
async def list_postgres_databases(
        analytics_handler: AnalyticsHandlerDep,
        token_detail: Annotated[TokenData, Depends(get_token_detail)]
) -> List[PostgresDatabaseDTO]:
    """List all PostgreSQL databases with their UIDs"""
    return await analytics_handler.list_postgres_databases()


@analytics_router.get("/databases/{database_uid}", response_model=DatabaseDTO)
async def get_database(
        database_uid: str,
        analytics_handler: AnalyticsHandlerDep,
) -> DatabaseDTO:
    """Get database by UID"""
    return await analytics_handler.get_database_by_uid(database_uid)


@analytics_router.get("/databases/{database_uid}/tables/{table_uid}", response_model=TableDTO)
async def get_table(
        database_uid: str,
        table_uid: str,
        analytics_handler: AnalyticsHandlerDep,
) -> TableDTO:
    """Get table by UID"""
    return await analytics_handler.get_table_by_uid(database_uid, table_uid)


@analytics_router.post("/postgres/databases", response_model=PostgresDatabaseDTO)
async def create_postgres_database(
        request: CreatePostgresDatabaseRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep,
) -> PostgresDatabaseDTO:
    """Create/Connect to a PostgreSQL database and map its schema"""
    # Set user_id from token in the request
    request.set_user_id(token_detail.user_id)
    return await analytics_handler.create_postgres_database(request)


@analytics_router.post("/excel/database", response_model=ExcelDatabaseDTO)
async def create_excel_database(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep,
        database_name: str = Form(...),
        excel_file: UploadFile = File(...),
        description: Optional[str] = Form(None),
) -> ExcelDatabaseDTO:
    """Create a new Excel database from uploaded file"""
    try:
        # Validate file is Excel format
        valid_excel_mime_types = [
            "application/vnd.ms-excel",  # .xls
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",  # .xlsx
            "application/vnd.ms-excel.sheet.macroEnabled.12"  # .xlsm
        ]
        
        # Check content type
        if excel_file.content_type not in valid_excel_mime_types:
            # Also check filename extension as fallback
            filename = excel_file.filename
            if filename is None or not (filename.lower().endswith('.xlsx') or filename.lower().endswith('.xls') or filename.lower().endswith('.xlsm')):
                raise HTTPException(
                    status_code=400, 
                    detail="Invalid file format. Only Excel files (.xlsx, .xls, .xlsm) are accepted."
                )
        
        # Create request DTO
        request = ExcelUploadRequestDTO(
            database_name=database_name,
            description=description or "Excel database"
        )
        # Set user_id from token in the request
        request.set_user_id(token_detail.user_id)

        return await analytics_handler.create_excel_database(request, excel_file)
    except AnalyticsError as e:
        raise e.to_http_exception()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.post("/csv/databases", response_model=CSVDatabaseDTO)
async def create_csv_database(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep,
        database_name: str = Form(...),
        files: List[UploadFile] = File(...),
        description: str = Form(None),
        settings: str = Form("{}")
) -> CSVDatabaseDTO:
    """Create a new CSV database from uploaded files"""
    try:
        settings_dict = json.loads(settings)

        request = CreateCSVDatabaseRequestDTO(
            database_name=database_name,
            description=description,
            settings=settings_dict
        )
        # Set user_id from token in the request
        request.set_user_id(token_detail.user_id)

        return await analytics_handler.create_csv_database(request, files)

    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid settings JSON")


@analytics_router.put("/csv/databases/{database_uid}/files", response_model=CSVDatabaseDTO)
async def add_csv_files(
        database_uid: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep,
        files: List[UploadFile] = File(...)
) -> CSVDatabaseDTO:
    """Add more CSV files to an existing database"""
    return await analytics_handler.add_csv_files(
        database_uid=database_uid,
        user_id=token_detail.user_id,
        csv_files=files
    )


@analytics_router.post("/schema/postgres", response_model=SchemaResponseDTO)
async def map_postgres_schema(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep,
        database_name: Optional[str] = None,
        database_uid: Optional[str] = None
) -> SchemaResponseDTO:
    """Map PostgreSQL database schema
    
    Either database_name or database_uid must be provided.
    """
    if not database_name and not database_uid:
        raise HTTPException(
            status_code=422,
            detail="Either database_name or database_uid must be provided"
        )

    return await analytics_handler.map_postgres_schema(
        database_name=database_name,
        database_uid=database_uid,
        user_id=token_detail.user_id
    )


@analytics_router.delete("/databases/{database_uid}/tables/{table_uid}/soft")
async def soft_delete_table(
        database_uid: str,
        table_uid: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> dict:
    """Soft delete a table"""
    await analytics_handler.soft_delete_table(
        database_uid=database_uid,
        table_uid=table_uid,
        user_id=token_detail.user_id
    )
    return {"message": "Table soft deleted successfully"}


@analytics_router.post("/databases/{database_uid}/tables/{table_uid}/restore")
async def restore_table(
        database_uid: str,
        table_uid: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> dict:
    """Restore a soft-deleted table"""
    await analytics_handler.restore_table(
        database_uid=database_uid,
        table_uid=table_uid,
        user_id=token_detail.user_id
    )
    return {"message": "Table restored successfully"}


@analytics_router.delete("/databases/{database_uid}/soft")
async def soft_delete_database(
        database_uid: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> dict:
    """Soft delete a database and all its tables"""
    await analytics_handler.soft_delete_database(
        database_uid=database_uid,
        user_id=token_detail.user_id
    )
    return {"message": "Database soft deleted successfully"}


@analytics_router.post("/databases/{database_uid}/restore")
async def restore_database(
        database_uid: str,
        request: RestoreDatabaseRequest,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> dict:
    """Restore a soft-deleted database"""
    await analytics_handler.restore_database(
        database_uid=database_uid,
        user_id=token_detail.user_id,
        restore_tables=request.restore_tables
    )
    return {"message": "Database restored successfully"}


@analytics_router.get("/databases/{database_uid}/tables/deleted", response_model=List[TableDTO])
async def list_deleted_tables(
        database_uid: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> List[TableDTO]:
    """Get all soft-deleted tables in a database"""
    return await analytics_handler.get_deleted_tables(
        database_uid=database_uid,
        user_id=token_detail.user_id
    )


# Chart endpoints

@analytics_router.post("/charts", response_model=ChartResponseDTO, status_code=201)
async def create_chart(
        request: CreateChartRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        chart_service: ChartServiceDep
) -> ChartResponseDTO:
    """
    Create a new chart from message data (synchronous)
    
    Args:
        request: Chart creation request
        token_detail: User token details
        chart_service: Chart service
        
    Returns:
        New chart data
    """
    try:
        # Create chart
        chart = await chart_service.create_chart(
            message_id=request.message_id,
            user_id=token_detail.user_id,
            org_id=token_detail.org_id,
            visibility=request.visibility.value,
            force_create=request.force_create,
            adjustment_query=request.adjustment_query
        )

        # PATCH: Set alternative visualizations from available_adjustments if not present
        chart_response = ChartResponseDTO.from_entity(chart)
        if chart_response.alternative_visualizations is None and chart_response.available_adjustments and 'alternative_visualizations' in chart_response.available_adjustments:
            import logging
            logger = logging.getLogger(__name__)
            logger.info(f"PATCH: Setting alternative_visualizations from available_adjustments for chart {chart.uid}")
            chart_response.alternative_visualizations = chart_response.available_adjustments[
                'alternative_visualizations']

        return chart_response

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@analytics_router.post("/charts/async", response_model=ChartTaskResponseDTO, status_code=202)
async def create_chart_async(
        request: CreateChartRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> ChartTaskResponseDTO:
    """
    Create a chart asynchronously
    
    Args:
        request: Chart creation request
        token_detail: User token details
        analytics_handler: Analytics handler service
        
    Returns:
        Task ID for tracking progress
    """
    try:
        # Create task and queue it
        task = await analytics_handler.create_chart_task(
            message_id=request.message_id, # type: ignore
            user_id=token_detail.user_id,
            org_id=token_detail.org_id,
            visibility=request.visibility.value,
            force_create=request.force_create,
            adjustment_query=request.adjustment_query
        )
        
        return ChartTaskResponseDTO(
            task_id=task.task_id,
            status=task.status,
            progress=task.progress,
            current_step=task.current_step,
            error_message=task.error_message,
            created_at=task.created_at,
            started_at=task.started_at,
            completed_at=task.completed_at,
            estimated_completion=task.estimated_completion,
            message="Chart generation queued successfully",
            message_id=str(request.message_id)
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@analytics_router.get("/charts/async/{task_id}/status", response_model=ChartTaskResponseDTO)
async def get_chart_task_status(
        task_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> ChartTaskResponseDTO:
    """Get chart generation task status"""
    try:
        task_status = await analytics_handler.get_chart_task_status(
            task_id=task_id,
            user_id=token_detail.user_id
        )
        
        if not task_status:
            raise HTTPException(status_code=404, detail="Task not found")
            
        return task_status
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/charts/async/{task_id}/result", response_model=ChartResponseDTO)
async def get_chart_result(
        task_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> ChartResponseDTO:
    """Get completed chart result"""
    try:
        chart = await analytics_handler.get_chart_by_task_id(
            task_id=task_id,
            user_id=token_detail.user_id
        )
        
        if not chart:
            raise HTTPException(status_code=404, detail="Chart not found or not completed")
            
        return chart
        
    except HTTPException:
        # Re-raise HTTPExceptions to preserve their status codes
        raise
    except Exception as e:
        import logging
        logger = logging.getLogger(__name__)
        logger.error(f"Error getting chart result for task {task_id}: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Internal server error: {str(e)}")


@analytics_router.delete("/charts/async/{task_id}")
async def cancel_chart_task(
        task_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        analytics_handler: AnalyticsHandlerDep
) -> dict:
    """Cancel a running chart generation task"""
    try:
        success = await analytics_handler.cancel_chart_task(
            task_id=task_id,
            user_id=token_detail.user_id
        )
        
        if success:
            return {"message": "Task cancelled successfully"}
        else:
            raise HTTPException(status_code=404, detail="Task not found or cannot be cancelled")
            
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@analytics_router.get("/charts/{chart_id}", response_model=ChartResponseDTO)
async def get_chart(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        chart_service: ChartServiceDep,
        chart_id: str = Path(..., description="ID of the chart to retrieve")
) -> ChartResponseDTO:
    """
    Get a chart by ID
    
    Args:
        token_detail: User token details
        chart_service: Chart service
        chart_id: ID of the chart to retrieve
        
    Returns:
        Chart data
    """
    try:
        chart = await chart_service.get_chart(
            chart_id=chart_id,
            user_id=token_detail.user_id,
            org_id=token_detail.org_id
        )

        # PATCH: Set alternative visualizations from available_adjustments if not present
        chart_response = ChartResponseDTO.from_entity(chart)
        if chart_response.alternative_visualizations is None and chart_response.available_adjustments and 'alternative_visualizations' in chart_response.available_adjustments:
            print("")
        return chart_response

    except ChartNotFoundError:
        raise HTTPException(
            status_code=404,
            detail=f"Chart not found: {chart_id}"
        )
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@analytics_router.get("/charts", response_model=ChartsListResponseDTO)
async def list_charts(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        chart_service: ChartServiceDep,
        limit: int = Query(20, description="Maximum number of charts to return"),
        offset: int = Query(0, description="Offset for pagination"),
        visibility: Optional[str] = Query(None, description="Filter by visibility"),
        user_id: Optional[str] = Query(None, description="Filter by user ID")
) -> ChartsListResponseDTO:
    """List all charts with pagination"""
    try:
        charts, total_count = await chart_service.list_charts(
            user_id=token_detail.user_id,
            org_id=token_detail.org_id,
            limit=limit,
            offset=offset,
        )
        return ChartsListResponseDTO(
            items=[ChartResponseDTO.from_entity(chart) for chart in charts],
            total=total_count
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to list charts: {str(e)}")


@analytics_router.get("/charts/by-message/{message_id}", response_model=MessageChartsResponseDTO)
async def get_charts_and_active_tasks_by_message(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        chart_service: ChartServiceDep,
        analytics_handler: AnalyticsHandlerDep,
        message_id: str = Path(..., description="ID of the message to get charts for")
) -> MessageChartsResponseDTO:
    """Get all charts and active tasks for a specific message"""
    try:
        # Get completed charts
        charts = await chart_service.get_charts_by_message(
            message_id=UUID(message_id),
            user_id=token_detail.user_id,
            org_id=token_detail.org_id,
        )
        
        # Get active tasks
        active_tasks = await analytics_handler.get_active_chart_tasks_by_message(
            message_id=message_id,
            user_id=token_detail.user_id
        )
        
        return MessageChartsResponseDTO(
            charts=[ChartResponseDTO.from_entity(chart) for chart in charts],
            active_tasks=active_tasks,
            has_active_tasks=len(active_tasks) > 0
        )
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to retrieve charts and tasks: {str(e)}")


@analytics_router.put("/charts/{chart_id}", response_model=ChartResponseDTO)
async def update_chart(
        request: UpdateChartRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        chart_service: ChartServiceDep,
        chart_id: str = Path(..., description="ID of the chart to update")
) -> ChartResponseDTO:
    """Update chart metadata"""
    try:
        chart = await chart_service.update_chart(
            chart_id=chart_id,
            user_id=token_detail.user_id,
            org_id=token_detail.org_id,
            title=request.title,
            description=request.description,
            visibility=request.visibility
        )
        return ChartResponseDTO.from_entity(chart)
    except ChartNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ChartUpdateError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update chart: {str(e)}")


@analytics_router.put("/charts/{chart_id}/dimensions", response_model=ChartResponseDTO)
async def update_chart_dimensions(
        dimensions: ChartDimensionsDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        chart_service: ChartServiceDep,
        chart_id: str = Path(..., description="ID of the chart to update dimensions for")
) -> ChartResponseDTO:
    """Update chart dimensions without LLM validation"""
    try:
        # Get the existing chart
        chart = await chart_service.get_chart(chart_id, user_id=token_detail.user_id, org_id=token_detail.org_id,)

        # Update dimensions directly in schema
        updated_schema = chart.chart_schema.copy()
        updated_schema["width"] = dimensions.width
        updated_schema["height"] = dimensions.height

        # Get the field mappings if it exists
        field_mappings = getattr(chart, 'available_field_mappings', None)

        # Save updated schema
        updated_chart = await chart_service.chart_repository.update_chart_data(
            chart_id=chart_id,
            user_id=token_detail.user_id,
            chart_data=chart.chart_data,
            chart_schema=updated_schema,
            available_adjustments=field_mappings,  # This field will be renamed in the repository
            chart_type=chart.chart_type
        )

        if not updated_chart:
            raise HTTPException(status_code=500, detail="Failed to update chart dimensions")

        return ChartResponseDTO.from_entity(updated_chart)

    except ChartNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to update chart dimensions: {str(e)}")



@analytics_router.post("/charts/{chart_id}/refresh", response_model=ChartResponseDTO)
async def refresh_chart(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        chart_service: ChartServiceDep,
        chart_id: str = Path(..., description="ID of the chart to refresh")
) -> ChartResponseDTO:
    """Refresh chart data by re-executing the original code"""
    try:
        chart = await chart_service.refresh_chart(
            chart_id=chart_id,
            user_id=token_detail.user_id,
            org_id=token_detail.org_id,
        )
        return ChartResponseDTO.from_entity(chart)
    except ChartNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except MessageNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except ChartRefreshError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to refresh chart: {str(e)}")




@analytics_router.delete("/charts/{chart_id}", status_code=204)
async def delete_chart(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        chart_service: ChartServiceDep,
        chart_id: str = Path(..., description="ID of the chart to delete")
) -> None:
    """Delete a chart"""
    try:
        await chart_service.delete_chart(
            chart_id=chart_id,
            user_id=token_detail.user_id,
        )
    except ChartNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete chart: {str(e)}")


@analytics_router.post("/recommendation", response_model=RecommendationResponseDTO)
async def get_recommendations(
        request: RecommendationRequestDTO,
        analytics_handler: AnalyticsHandlerDep,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],):
    """Get query recommendations based on database schema"""
    try:

        return await analytics_handler.get_recommendations(
            database_uid=request.database_uid,
            table_uid=request.table_uid,
            count=request.count,
        )
    except AnalyticsError as e:
        raise e.to_http_exception()
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


# Dashboard routes
@analytics_router.post("/dashboards", response_model=DashboardResponseDTO, status_code=201)
async def create_dashboard(
        request: CreateDashboardRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> DashboardResponseDTO:
    """Create a new dashboard"""
    return await dashboard_handler.create_dashboard(
        request=request,
        requested_user_id=token_detail.user_id,
        org_id=token_detail.org_id
    )


@analytics_router.get("/dashboards", response_model=List[DashboardResponseDTO])
async def list_dashboards(
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> List[DashboardResponseDTO]:
    """List all dashboards accessible to the user"""
    return await dashboard_handler.list_dashboards(
        requested_user_id=token_detail.user_id
    )


@analytics_router.get("/dashboards/{dashboard_id}", response_model=DashboardResponseDTO)
async def get_dashboard(
        dashboard_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep,
        sync: Optional[bool] = Query(None, description="Whether to sync the dashboard data")
) -> DashboardResponseDTO:
    """Get a specific dashboard by ID"""
    return await dashboard_handler.get_dashboard(
        dashboard_id=dashboard_id,
        requested_user_id=token_detail.user_id,
        sync=sync
    )


@analytics_router.put("/dashboards/{dashboard_id}", response_model=DashboardResponseDTO)
async def update_dashboard(
        dashboard_id: str,
        request: UpdateDashboardRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> DashboardResponseDTO:
    """Update a dashboard"""
    return await dashboard_handler.update_dashboard(
        dashboard_id=dashboard_id,
        request=request,
        requested_user_id=token_detail.user_id
    )


@analytics_router.delete("/dashboards/{dashboard_id}")
async def delete_dashboard(
        dashboard_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> dict:
    """Delete a dashboard"""
    return await dashboard_handler.delete_dashboard(
        dashboard_id=dashboard_id,
        requested_user_id=token_detail.user_id
    )


@analytics_router.post("/dashboards/{dashboard_id}/restore", response_model=DashboardResponseDTO)
async def restore_dashboard(
        dashboard_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> DashboardResponseDTO:
    """Restore a deleted dashboard"""
    return await dashboard_handler.restore_dashboard(
        dashboard_id=dashboard_id,
        user_id=token_detail.user_id
    )


@analytics_router.post("/dashboards/{dashboard_id}/charts", response_model=DashboardResponseDTO)
async def add_chart_to_dashboard(
        dashboard_id: str,
        request: AddChartToDashboardRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> DashboardResponseDTO:
    """
    Add a chart to a dashboard
    
    Args:
        dashboard_id: The dashboard ID
        request: Chart information (minimum required is chart_id)
        token_detail: User token data
        dashboard_handler: Dashboard handler service
        
    Returns:
        Updated dashboard information
    """
    return await dashboard_handler.add_chart_to_dashboard(
        dashboard_id=dashboard_id,
        chart_id=request.chart_id,
        user_id=token_detail.user_id,
        org_id=token_detail.org_id
    )


@analytics_router.delete("/dashboards/{dashboard_id}/charts/{chart_id}", response_model=DashboardResponseDTO)
async def remove_chart_from_dashboard(
        dashboard_id: str,
        chart_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> DashboardResponseDTO:
    """
    Remove a chart from a dashboard
    
    Args:
        dashboard_id: The dashboard ID
        chart_id: The chart ID to remove
        token_detail: User token data
        dashboard_handler: Dashboard handler service
        
    Returns:
        Updated dashboard information
    """
    return await dashboard_handler.remove_chart_from_dashboard(
        dashboard_id=dashboard_id,
        chart_id=chart_id,
        requested_user_id=token_detail.user_id,
        org_id=token_detail.org_id
    )


# Dashboard collaboration routes
@analytics_router.post("/dashboards/{dashboard_id}/share", response_model=DashboardResponseDTO)
async def share_dashboard(
        dashboard_id: str,
        request: ShareDashboardRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        collaboration_handler: DashboardCollaborationHandlerDep
) -> DashboardResponseDTO:
    """Share a dashboard with multiple users"""
    return await collaboration_handler.share_dashboard(
        dashboard_id=dashboard_id,
        request=request,
        requested_user_id=token_detail.user_id
    )


@analytics_router.delete("/dashboards/{dashboard_id}/share/{user_id}", response_model=DashboardResponseDTO)
async def remove_user_access(
        dashboard_id: str,
        user_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        collaboration_handler: DashboardCollaborationHandlerDep
) -> DashboardResponseDTO:
    """Remove a user's access to a dashboard"""
    return await collaboration_handler.remove_user_access(
        dashboard_id=dashboard_id,
        requested_user_id=user_id, # The user whose access is being removed
        user_id=token_detail.user_id # The user who is removing the access(determined by the token)
    )   


@analytics_router.put("/dashboards/{dashboard_id}/share/{user_id}", response_model=DashboardResponseDTO)
async def update_user_permission(
        dashboard_id: str,
        user_id: str,
        request: UpdatePermissionRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        collaboration_handler: DashboardCollaborationHandlerDep
) -> DashboardResponseDTO:
    """Update a user's permission level for a dashboard"""
    return await collaboration_handler.update_user_permission(
        dashboard_id=dashboard_id,
        user_id=user_id,
        request=request,
        requested_user_id=token_detail.user_id
    )


@analytics_router.get("/dashboards/{dashboard_id}/share", response_model=DashboardAccessResponseDTO)
async def get_dashboard_access(
        dashboard_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        collaboration_handler: DashboardCollaborationHandlerDep
) -> DashboardAccessResponseDTO:
    """Get list of users with access to a dashboard"""
    return await collaboration_handler.get_dashboard_access(
        dashboard_id=dashboard_id,
        user_id=token_detail.user_id
    )


# Add these routes after the dashboard chart routes

@analytics_router.post("/dashboards/{dashboard_id}/dataframes", response_model=DashboardResponseDTO)
async def add_dataframe_to_dashboard(
        dashboard_id: str,
        request: AddDataframeRequestDTO,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> DashboardResponseDTO:
    """
    Add a dataframe to a dashboard
    
    Creates a new dataframe and adds it to the specified dashboard.
    The dataframe will be stored as part of the dashboard visualization.
    """
    try:
        return await dashboard_handler.add_dataframe_to_dashboard(
            dashboard_id=dashboard_id,
            request=request,
            requested_user_id=token_detail.user_id
        )
    except (DashboardNotFoundError, DashboardAccessDeniedError, InsufficientPermissionError) as e:
        # These exceptions are already handled by the handler
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )

@analytics_router.delete("/dashboards/{dashboard_id}/dataframes/{dataframe_id}", response_model=DashboardResponseDTO)
async def remove_dataframe_from_dashboard(
        dashboard_id: str,
        dataframe_id: str,
        token_detail: Annotated[TokenData, Depends(get_token_detail)],
        dashboard_handler: DashboardHandlerDep
) -> DashboardResponseDTO:
    """
    Remove a dataframe from a dashboard
    
    Removes the association between a dataframe and a dashboard.
    Note that the dataframe relationship will be removed, but the dataframe itself may still exist.
    """
    try:
        return await dashboard_handler.remove_dataframe_from_dashboard(
            dashboard_id=dashboard_id,
            dataframe_id=dataframe_id,
            requested_user_id=token_detail.user_id
        )
    except (DashboardNotFoundError, DashboardAccessDeniedError, InsufficientPermissionError) as e:
        # These exceptions are already handled by the handler
        raise
    except Exception as e:
        # Catch any unexpected errors
        raise HTTPException(
            status_code=500,
            detail=f"An unexpected error occurred: {str(e)}"
        )


# WebSocket and SSE routes for real-time chart updates
async def poll_chart_task_updates(
    task_id: str, 
    queue_service: ChartQueueService, 
    request: Request
) -> AsyncGenerator[bytes, None]:
    """
    Async generator function to poll for chart task updates and yield streaming data.
    """
    last_check_time = None
    
    print(f"[Stream: {task_id}] Connection established. Starting polling.")

    try:
        while True:
            # Check if client disconnected
            if await request.is_disconnected():
                print(f"[Stream: {task_id}] Client disconnected.")
                break

            # Get task status
            status_data = await queue_service.get_task_status(task_id)
            if not status_data:
                print(f"[Stream: {task_id}] Task not found. Closing connection.")
                yield f"data: {json.dumps({'type': 'error', 'message': 'Task not found'})}\n\n".encode('utf-8')
                break
            
            # Send status update
            yield (
                f"id: {task_id}\n"
                f"event: status_update\n"
                f"data: {json.dumps(status_data['status'])}\n\n"
            ).encode('utf-8')
            
            # Check if task is complete
            if status_data["status"] in ["COMPLETED", "FAILED", "CANCELLED"]:
                print(f"[Stream: {task_id}] Task completed with status: {status_data['status']}")
                break
            
            # Wait before next poll
            await asyncio.sleep(2)  # 2 second polling interval

    except Exception as e:
        print(f"[Stream: {task_id}] Error in polling: {e}")
        yield (
            f"id: {task_id}\n"
            f"event: error\n"
            f"data: {json.dumps({'message': str(e)})}\n\n"
        ).encode('utf-8')


@analytics_router.get("/charts/stream/{task_id}")
async def stream_chart_task_updates(
    task_id: str, 
    request: Request,
    queue_service: ChartQueueServiceDep
):
    """
    Streaming endpoint to stream progress updates for a chart generation task.
    Clients connect here with the task_id received after initiating chart generation.
    """
    print(f"Received streaming connection request for task_id: {task_id}")
    
    # Initial check if task exists
    status_data = await queue_service.get_task_status(task_id)
    if not status_data:
        print(f"Task {task_id} not found during initial check.")
        raise HTTPException(status_code=404, detail="Task not found")

    event_generator = poll_chart_task_updates(task_id, queue_service, request)
    return StreamingResponse(
        event_generator,
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream"
        }
    )


@analytics_router.websocket("/charts/ws/{task_id}")
async def chart_status_websocket(
    websocket: WebSocket,
    task_id: str,
    queue_service: ChartQueueServiceDep,
    token_detail: Any = Depends(get_token_detail)
):
    """WebSocket endpoint for real-time chart generation updates"""
    await websocket.accept()
    
    try:
        # Subscribe to Redis channel for this task using the injected queue service
        redis_client = queue_service.redis  # Get Redis client from queue service
        redis_channel = f"chart_generation:updates:{task_id}"
        pubsub = redis_client.create_pubsub()
        pubsub.subscribe(redis_channel)
        
        # Send initial status
        initial_status = await queue_service.get_task_status(task_id)
        if initial_status:
            await websocket.send_text(json.dumps(initial_status))
        
        # Listen for updates
        while True:
            try:
                message = pubsub.get_message(timeout=1.0)
                if message and message['type'] == 'message':
                    await websocket.send_text(message['data'])
                    
                    # Check if task is complete
                    status_data = json.loads(message['data'])
                    if status_data['status'] in ['COMPLETED', 'FAILED', 'CANCELLED']:
                        break
                        
            except Exception as e:
                print(f"WebSocket error: {str(e)}")
                break
                
    except WebSocketDisconnect:
        print(f"WebSocket disconnected for task {task_id}")
    finally:
        pubsub.close()
