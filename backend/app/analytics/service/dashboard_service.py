import logging
from typing import Dict, List, Any, Optional, Tuple
from datetime import datetime
import uuid
import json

from app.analytics.repository.schema.models.dashboard import Dashboard
from app.analytics.repository.schema.models.dataframe import Dataframe as DBDataframe
from app.analytics.repository.schema.models.chart import Chart
from app.analytics.entity.dataframe import Dataframe
from app.analytics.repository.dashboard_repository import DashboardRepository
from app.analytics.errors import (
    DashboardNotFoundError,
    DashboardAccessDeniedError,
    DashboardCreationError,
    DashboardUpdateError,
    ChartNotFoundError,
    InsufficientPermissionError,
    DataframeCreationError
)
from pkg.log.logger import Logger
from app.chat.service.chat_service import ChatService
from app.pal.analytics.adapters.analytics_repository_adapter import AnalyticsRepositoryAdapter
from app.pal.analytics.utils.code_execution import execute_sql
from app.analytics.utils.generateDFContent import generate_dataframe_content
from app.analytics.repository.chart_repository import ChartRepository
class DashboardService:
    """Service for dashboard-related operations"""

    def __init__(self, logger: Logger, dashboard_repository: DashboardRepository, chat_service: ChatService, analytics_repository: AnalyticsRepositoryAdapter, chart_repository: ChartRepository):

        self.logger = logger
        self.dashboard_repository = dashboard_repository
        self.chat_service = chat_service
        self.analytics_repository = analytics_repository
        self.chart_repository = chart_repository

    async def create_dashboard(self, requested_user_id: str, org_id:str, title: str, description: Optional[str] = None,
        layout_config: Optional[Dict[str, Any]] = None, layouts: Optional[Dict[str, Any]] = None) -> Dashboard:
        """
        Create a new dashboard
        
        Args:
            requested_user_id: User id
            title: Dashboard title
            description: Optional description of the dashboard
            layout_config: Optional layout configuration
            layouts: Optional chart layouts
            
        Returns:
            The created Dashboard entity
        """
        self.logger.info(f"Creating dashboard '{title}' for user {requested_user_id}")
        
        try:
            dashboard = Dashboard.create_dashboard(
                title=title,
                user_id=requested_user_id,
                org_id=org_id,
                description=description or "",
                layout_config=layout_config or {}
            )
            
            if layouts:
                dashboard.layouts = layouts
                dashboard.save()
                
            self.logger.info(f"Dashboard created successfully with ID: {dashboard.dashboard_id}")
            return dashboard
        except Exception as e:
            self.logger.error(f"Error creating dashboard: {str(e)}")
            raise DashboardCreationError(f"Failed to create dashboard: {str(e)}")
    
    async def get_dashboard(self, dashboard_id: str, requested_user_id: str) -> Dashboard:
        """
        Get a dashboard by ID
        
        Args:
            dashboard_id: The dashboard's unique ID
            requested_user_id: requested_user_id
            
        Returns:
            The Dashboard entity
            
        Raises:
            DashboardNotFoundError: If the dashboard is not found
            DashboardAccessDeniedError: If the user doesn't have access to the dashboard
        """
        self.logger.info(f"Fetching dashboard {dashboard_id}")
        
        try:
            dashboard = Dashboard.nodes.get(dashboard_id=dashboard_id, is_deleted=False)
        except Dashboard.DoesNotExist:
            self.logger.error(f"Dashboard {dashboard_id} not found")
            raise DashboardNotFoundError(dashboard_id)
        
        # Check access permissions
        # 1. User is the owner - full access
        if dashboard.user_id == requested_user_id:
            return dashboard
            
        # 2. Check for specific user access via collaboration relationship
        from neomodel import db
        
        query = """
        MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:SHARED_WITH]->(u:User {uid: $user_id})
        RETURN r.permission as permission
        """
        
        params = {
            'dashboard_id': dashboard_id,
            'user_id': requested_user_id
        }
        
        results, _ = db.cypher_query(query, params)
        
        if not results or len(results) == 0:
            self.logger.error(f"User {requested_user_id} does not have access to dashboard {dashboard_id}")
            raise DashboardAccessDeniedError()
        
        self.logger.info(f"User {requested_user_id} has '{results[0][0]}' access to dashboard {dashboard_id}")
        return dashboard

    async def _sync_entity(self, entity: Any, requested_user_id: str) -> Tuple[Optional[Dict], Optional[str]]:
        """
        Common sync logic for both dataframes and charts
        
        Args:
            entity: The entity to sync (either DataFrame or Chart)
            requested_user_id: User ID requesting the sync
            
        Returns:
            Tuple of (content, error) where content is the generated content and error is any error message
        """
        if not hasattr(entity, 'message_id') or not entity.message_id or not self.chat_service:
            return None, None
            
        message = await self.chat_service.get_message(user_id=requested_user_id, message_id=entity.message_id)
        
        database_uid = None
        database_type = None
        code = None
        columns = None

        # Extract database_id
        if message.database_uid:
            self.logger.info(f"Database ID: {message.database_uid}")
            db_info = await self.analytics_repository.get_database_info(message.database_uid)
            self.logger.info(f"Database Info: {db_info}")
            database_uid = db_info.uid
            database_type = db_info.type

        # Extract code from artifacts
        code_artifacts = [artifact for artifact in message.artifacts if artifact.artifact_type == "code"]
        for code_artifact in code_artifacts:
            self.logger.info(f"Code: {code_artifact.content}")
            code = code_artifact.content

        # Extract columns from artifacts
        columns_artifacts = [artifact for artifact in message.artifacts if artifact.artifact_type == "columns"]
        for columns_artifact in columns_artifacts:
            self.logger.info(f"Columns: {columns_artifact.content}")
            columns = columns_artifact.content

        # Sync is only supported for postgres databases
        if database_type == 'postgres':
            # Execute code
            result, error = await execute_sql(
                query=code,
                repository_adapter=self.analytics_repository,
                database_uid=database_uid,
                logger=self.logger
            )
            self.logger.info(f"Result: {result}")
            self.logger.info(f"Error: {error}")
            
            if result is not None and not error:
                # Generate content using the utility function with existing columns
                content = generate_dataframe_content(json.loads(columns), result)
                return content, None
                
        return None, "Unsupported database type or execution error"

    async def _sync_dataframe(self, dataframe: DBDataframe, requested_user_id: str) -> None:
        """
        Sync a single dataframe by executing its associated SQL query
        
        Args:
            dataframe: The dataframe to sync
            requested_user_id: User ID requesting the sync
        """
        content, error = await self._sync_entity(dataframe, requested_user_id)
        if content:
            dataframe.update(content=content)

    async def _sync_chart(self, chart: Chart, requested_user_id: str) -> None:
        """
        Sync a single chart by executing its associated code

        Args:
            chart: The chart to sync
            requested_user_id: User ID requesting the sync
        """
        content, error = await self._sync_entity(chart, requested_user_id)
        if content:
            chart.update(chart_data=json.loads(content))

    async def sync_dashboard(self, dashboard_id: str, requested_user_id: str) -> Dashboard:
        """
        Sync a dashboard by getting the latest data for all dataframes and charts
        Basically, it will execute the code and update the content of the dataframes and charts
        
        Args:
            dashboard_id: The dashboard's unique ID
            requested_user_id: User ID requesting the sync
            
        Returns:
            The updated Dashboard entity
            
        Raises:
            DashboardNotFoundError: If the dashboard is not found
            DashboardAccessDeniedError: If the user doesn't have access to the dashboard
        """
        self.logger.info(f"Syncing dashboard {dashboard_id}")
        try:
            # Get the dashboard (this will check basic access permission)
            dashboard = await self.get_dashboard(dashboard_id, requested_user_id)
            
            # Sync each dataframe
            for dataframe in dashboard.dataframes:
                await self._sync_dataframe(dataframe, requested_user_id)

            # Sync each chart
            for chart in dashboard.charts:
                await self._sync_chart(chart, requested_user_id)

            return dashboard

        except Exception as e:
            self.logger.error(f"Error syncing dashboard {dashboard_id}: {str(e)}")
            raise e

    async def list_dashboards(self,  requested_user_id: str) -> List[Dashboard]:

        self.logger.info(f"Listing dashboards for user {requested_user_id}")
        
        # Query for dashboards belonging to the user
        dashboards = list(Dashboard.nodes.filter(is_deleted=False, user_id=requested_user_id))
        

        # Add dashboards shared with the user
        from neomodel import db
        
        query = """
        MATCH (d:Dashboard {is_deleted: false})-[r:SHARED_WITH]->(u:User {uid: $user_id})
        RETURN d
        """
        
        params = {
            'user_id': requested_user_id
        }
        
        results, _ = db.cypher_query(query, params)
        
        if results and len(results) > 0:
            for record in results:
                shared_dashboard = Dashboard.inflate(record[0])
                if shared_dashboard not in dashboards:
                    dashboards.append(shared_dashboard)
        
        return dashboards
    
    async def update_dashboard(self,  dashboard_id: str, requested_user_id: str, title: Optional[str] = None,
        description: Optional[str] = None, layout_config: Optional[Dict[str, Any]] = None,
                               layouts: Optional[Dict[str, Any]] = None) -> Dashboard:
        """
        Update a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            requested_user_id: User authentication requested_user_id
            title: Optional new title
            description: Optional new description
            layout_config: Optional new layout configuration
            layouts: Optional new chart layouts
            
        Returns:
            The updated Dashboard entity
            
        Raises:
            DashboardNotFoundError: If the dashboard is not found
            DashboardAccessDeniedError: If the user doesn't have permission to update the dashboard
            InsufficientPermissionError: If the user has view-only access
        """
        self.logger.info(f"Updating dashboard {dashboard_id}")
        
        # Get the dashboard (this will check basic access permission)
        dashboard = await self.get_dashboard(dashboard_id, requested_user_id)
        
        # Check for edit permission if user is not the owner
        if dashboard.user_id != requested_user_id:
            # Check for user's edit permission
            from neomodel import db
            
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:SHARED_WITH]->(u:User {uid: $user_id})
            RETURN r.permission as permission
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'user_id': requested_user_id
            }
            
            results, _ = db.cypher_query(query, params)
            
            if not results or len(results) == 0 or results[0][0] != "edit":
                self.logger.error(f"User {requested_user_id} doesn't have edit permission for dashboard {dashboard_id}")
                raise InsufficientPermissionError("You need edit permission to modify this dashboard")
        
        try:
            # Update the dashboard
            dashboard = dashboard.update(
                title=title,
                description=description,
                layout_config=layout_config,
                layouts=layouts
            )
            
            self.logger.info(f"Dashboard {dashboard_id} updated successfully")
            return dashboard
        except Exception as e:
            self.logger.error(f"Error updating dashboard {dashboard_id}: {str(e)}")
            raise DashboardUpdateError(f"Failed to update dashboard: {str(e)}")
    
    async def delete_dashboard(self, dashboard_id: str, requested_user_id: str) -> bool:
        """
        Delete a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            requested_user_id: User id

        Returns:
            True if successfully deleted
            
        Raises:
            DashboardNotFoundError: If the dashboard is not found
            DashboardAccessDeniedError: If the user doesn't have permission to delete the dashboard
        """
        self.logger.info(f"Deleting dashboard {dashboard_id}")
        
        # Get the dashboard
        dashboard = await self.get_dashboard(dashboard_id, requested_user_id)
        
        # User must be the owner to delete the dashboard
        if dashboard.user_id != requested_user_id:
            self.logger.error(f"User {requested_user_id} doesn't have permission to delete dashboard {dashboard_id}")
            raise DashboardAccessDeniedError("Only the dashboard owner can delete the dashboard")
        
        try:
            # Soft delete the dashboard
            dashboard.soft_delete()
            self.logger.info(f"Dashboard {dashboard_id} soft deleted successfully")
            return True
        except Exception as e:
            self.logger.error(f"Error deleting dashboard {dashboard_id}: {str(e)}")
            return False
    
    async def restore_dashboard(self, dashboard_id: str, user_id: str) -> Dashboard:

        self.logger.info(f"Restoring dashboard {dashboard_id}")
        
        try:
            # Include deleted dashboards in the search
            dashboard = Dashboard.nodes.get(dashboard_id=dashboard_id, is_deleted=True)
        except Dashboard.DoesNotExist:
            self.logger.error(f"Dashboard {dashboard_id} not found")
            raise DashboardNotFoundError(dashboard_id)
        
        # User must be the owner to restore the dashboard
        if dashboard.user_id != user_id:
            self.logger.error(f"User {requested_user_id} doesn't have permission to restore dashboard {dashboard_id}")
            raise DashboardAccessDeniedError("Only the dashboard owner can restore the dashboard")
        
        try:
            # Restore the dashboard
            dashboard.restore()
            self.logger.info(f"Dashboard {dashboard_id} restored successfully")
            return dashboard
        except Exception as e:
            self.logger.error(f"Error restoring dashboard {dashboard_id}: {str(e)}")
            return None

    async def add_chart_to_dashboard(
        self,
        dashboard_id: str,
        chart_id: str,
        requested_user_id: str,
        org_id: str,
        chart_service=None
    ) -> Dashboard:
        """
        Add a chart to a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            chart_id: The chart's unique ID
            requested_user_id: User requested_user_id
            chart_service: Optional ChartService for validating the chart
            
        Returns:
            The updated Dashboard entity
            
        Raises:
            DashboardNotFoundError: If the dashboard is not found
            DashboardAccessDeniedError: If the user doesn't have permission to update the dashboard
            ChartNotFoundError: If the chart is not found or not accessible to the user
            InsufficientPermissionError: If the user has view-only access
        """
        self.logger.info(f"Adding chart {chart_id} to dashboard {dashboard_id}")
        
        # Get the dashboard
        dashboard = await self.get_dashboard(dashboard_id, requested_user_id)
        
        # Check for edit permission if user is not the owner
        if dashboard.user_id != requested_user_id:
            # Check for user's edit permission
            from neomodel import db
            
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:SHARED_WITH]->(u:User {uid: $user_id})
            RETURN r.permission as permission
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'user_id': requested_user_id
            }
            
            results, _ = db.cypher_query(query, params)
            
            if not results or len(results) == 0 or results[0][0] != "edit":
                self.logger.error(f"User {requested_user_id} doesn't have edit permission for dashboard {dashboard_id}")
                raise InsufficientPermissionError("You need edit permission to add charts to this dashboard")
        
        # Validate the chart exists and is accessible to the user if chart_service is provided
        if chart_service:
            try:
                chart = await chart_service.get_chart(chart_id, requested_user_id, org_id)
                if not chart:
                    raise ChartNotFoundError(f"Chart {chart_id} not found or not accessible")
            except Exception as e:
                self.logger.error(f"Error validating chart {chart_id}: {str(e)}")
                raise ChartNotFoundError(f"Chart validation failed: {str(e)}")
        
        try:
            # Create a Cypher query to add the relationship between the dashboard and chart
            from neomodel import db
            
            # Ensure both nodes exist and create the relationship
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id}), (c:Chart {uid: $chart_id})
            MERGE (d)-[:CONTAINS_CHART]->(c)
            RETURN d
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'chart_id': chart_id
            }
            
            # Execute the query
            results, _ = db.cypher_query(query, params)
            
            if not results or len(results) == 0:
                self.logger.error(f"Failed to add chart {chart_id} to dashboard {dashboard_id}")
                raise DashboardUpdateError(f"Failed to add chart to dashboard: No results from database")
            
            # Update the dashboard's updated_at timestamp
            dashboard.updated_at = datetime.utcnow().isoformat()
            dashboard.save()
            
            self.logger.info(f"Chart {chart_id} added to dashboard {dashboard_id} successfully via relationship")
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error adding chart to dashboard: {str(e)}")
            raise DashboardUpdateError(f"Failed to add chart to dashboard: {str(e)}")

    async def remove_chart_from_dashboard(
        self,
        dashboard_id: str,
        chart_id: str,
        requested_user_id: str,
            org_id: str,
        chart_service=None
    ) -> Dashboard:

        self.logger.info(f"Removing chart {chart_id} from dashboard {dashboard_id}")
        
        # Get the dashboard
        dashboard = await self.get_dashboard(dashboard_id, requested_user_id)
        
        # Check for edit permission if user is not the owner
        if dashboard.user_id != requested_user_id:
            # Check for user's edit permission
            from neomodel import db
            
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:SHARED_WITH]->(u:User {uid: $user_id})
            RETURN r.permission as permission
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'user_id': requested_user_id
            }
            
            results, _ = db.cypher_query(query, params)
            
            if not results or len(results) == 0 or results[0][0] != "edit":
                self.logger.error(f"User {requested_user_id} doesn't have edit permission for dashboard {dashboard_id}")
                raise InsufficientPermissionError("You need edit permission to remove charts from this dashboard")
        
        # Validate the chart exists and is accessible to the user if chart_service is provided
        if chart_service:
            try:
                chart = await chart_service.get_chart(chart_id, requested_user_id, org_id)
                if not chart:
                    raise ChartNotFoundError(f"Chart {chart_id} not found or not accessible")
            except Exception as e:
                self.logger.error(f"Error validating chart {chart_id}: {str(e)}")
                raise ChartNotFoundError(f"Chart validation failed: {str(e)}")
        
        try:
            # Create a Cypher query to remove the relationship between the dashboard and chart
            from neomodel import db
            
            # Remove the relationship
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:CONTAINS_CHART]->(c:Chart {uid: $chart_id})
            DELETE r
            RETURN d
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'chart_id': chart_id
            }
            
            # Execute the query
            results, _ = db.cypher_query(query, params)
            
            if not results or len(results) == 0:
                self.logger.error(f"Failed to remove chart {chart_id} from dashboard {dashboard_id}")
                raise DashboardUpdateError(f"Failed to remove chart from dashboard: No results from database")
            
            # Update the dashboard's updated_at timestamp
            dashboard.updated_at = datetime.utcnow().isoformat()
            dashboard.save()
            
            self.logger.info(f"Chart {chart_id} removed from dashboard {dashboard_id} successfully")
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error removing chart from dashboard: {str(e)}")
            raise DashboardUpdateError(f"Failed to remove chart from dashboard: {str(e)}")

    async def add_dataframe_to_dashboard(
        self,
        dashboard_id: str,
        requested_user_id: str,
        content: str,  # JSON string of dataframe content
        columns: str,  # JSON string of column definitions
        metadata: str = "{}",  # Additional metadata
        message_id: Optional[str] = None  # ID of the message that triggered this creation
    ) -> Tuple[Dashboard, Dataframe]:
        """
        Create a dataframe and add it to a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            requested_user_id: User ID requesting the operation
            content: JSON string containing dataframe content
            columns: JSON string defining column structure
            metadata: Optional metadata as JSON string
            message_id: Optional ID of the message that triggered this creation
            
        Returns:
            Tuple of (Updated Dashboard entity, Created Dataframe entity)
            
        Raises:
            DashboardNotFoundError: If the dashboard is not found
            DashboardAccessDeniedError: If the user doesn't have permission
            InsufficientPermissionError: If the user has view-only access
            DataframeCreationError: If the dataframe cannot be created
        """
        self.logger.info(f"Creating dataframe node and adding to dashboard {dashboard_id}")
        
        # Get the dashboard (this will check basic access permission)
        dashboard = await self.get_dashboard(dashboard_id, requested_user_id)
        
        # Check for edit permission if user is not the owner
        if dashboard.user_id != requested_user_id:
            # Use the dashboard repository to check for edit permission
            self.dashboard_repository.check_dashboard_edit_permission(
                dashboard_id=dashboard_id,
                user_id=requested_user_id,
                dashboard=dashboard
            )
        
        try:
            # Use the dashboard repository to create the dataframe and add it to the dashboard
            db_dashboard, db_dataframe = self.dashboard_repository.create_dataframe_and_add_to_dashboard(
                dashboard_id=dashboard_id,
                user_id=requested_user_id,
                content=content,
                columns=columns,
                metadata=metadata,
                message_id=message_id
            )
            
            # Convert DB model to entity model
            dataframe = Dataframe.from_db_model(db_dataframe)
            
            return db_dashboard, dataframe
            
        except Exception as e:
            self.logger.error(f"Error adding dataframe to dashboard: {str(e)}")
            raise DataframeCreationError(f"Failed to add dataframe to dashboard: {str(e)}")

    async def remove_dataframe_from_dashboard(
        self,
        dashboard_id: str,
        dataframe_id: str,
        requested_user_id: str,
    ) -> Dashboard:
        """
        Remove a dataframe from a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            dataframe_id: The dataframe's unique ID
            requested_user_id: User ID requesting the operation
            
        Returns:
            The updated Dashboard entity
            
        Raises:
            DashboardNotFoundError: If the dashboard is not found
            DashboardAccessDeniedError: If the user doesn't have permission
            InsufficientPermissionError: If the user has view-only access
            DataframeNotFoundError: If the dataframe is not found
        """
        self.logger.info(f"Removing dataframe {dataframe_id} from dashboard {dashboard_id}")
        
        # Get the dashboard (this will check basic access permission)
        dashboard = await self.get_dashboard(dashboard_id, requested_user_id)
        
        # Check for edit permission if user is not the owner
        if dashboard.user_id != requested_user_id:
            # Use the dashboard repository to check for edit permission
            self.dashboard_repository.check_dashboard_edit_permission(
                dashboard_id=dashboard_id,
                user_id=requested_user_id,
                dashboard=dashboard
            )
        
        try:
            # Use the dashboard repository to remove the dataframe from the dashboard
            updated_dashboard = self.dashboard_repository.remove_dataframe_from_dashboard(
                dashboard_id=dashboard_id,
                dataframe_id=dataframe_id
            )
            
            return updated_dashboard
            
        except Exception as e:
            self.logger.error(f"Error removing dataframe from dashboard: {str(e)}")
            raise DashboardUpdateError(f"Failed to remove dataframe from dashboard: {str(e)}")
