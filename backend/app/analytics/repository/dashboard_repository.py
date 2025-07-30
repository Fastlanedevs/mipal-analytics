import logging
from typing import Tuple, Optional
from neomodel import db
from datetime import datetime

from app.analytics.repository.schema.models.dashboard import Dashboard
from app.analytics.repository.schema.models.dataframe import Dataframe
from app.analytics.errors import DashboardUpdateError, DataframeCreationError, InsufficientPermissionError

class DashboardRepository:
    """Repository for dashboard-related database operations"""

    def __init__(self, logger=None):
        """
        Initialize the dashboard repository
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger or logging.getLogger(__name__)
    
    def check_dashboard_edit_permission(
        self,
        dashboard_id: str,
        user_id: str,
        dashboard: Optional[Dashboard] = None
    ) -> bool:
        """
        Check if a user has edit permission for a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            user_id: The user's ID
            dashboard: Optional Dashboard object to avoid extra query
            
        Returns:
            True if the user has edit permission, False otherwise
        
        Raises:
            InsufficientPermissionError: If the user doesn't have edit permission
        """
        # If dashboard is provided, check if user is the owner
        if dashboard and dashboard.user_id == user_id:
            return True
            
        # Check for specific user access via collaboration relationship
        query = """
        MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:SHARED_WITH]->(u:User {uid: $user_id})
        RETURN r.permission as permission
        """
        
        params = {
            'dashboard_id': dashboard_id,
            'user_id': user_id
        }
        
        results, _ = db.cypher_query(query, params)
        
        if not results or len(results) == 0 or results[0][0] != "edit":
            error_msg = f"User {user_id} doesn't have edit permission for dashboard {dashboard_id}"
            self.logger.error(error_msg)
            raise InsufficientPermissionError("You need edit permission to modify this dashboard")
            
        return True
    
    def add_dataframe_to_dashboard(
        self,
        dashboard_id: str,
        dataframe_id: str
    ) -> Dashboard:
        """
        Add a dataframe to a dashboard by creating a relationship
        
        Args:
            dashboard_id: The dashboard's unique ID
            dataframe_id: The dataframe's unique ID
            
        Returns:
            The updated Dashboard entity
            
        Raises:
            DashboardUpdateError: If the relationship cannot be created
        """
        try:
            # Create a relationship between the dashboard and the dataframe
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id}), (df:Dataframe {dataframe_id: $dataframe_id})
            MERGE (d)-[:CONTAINS_DATAFRAME]->(df)
            RETURN d
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'dataframe_id': dataframe_id
            }
            
            # Execute the query
            results, _ = db.cypher_query(query, params)
            
            if not results or len(results) == 0:
                self.logger.error(f"Failed to link dataframe {dataframe_id} to dashboard {dashboard_id}")
                raise DashboardUpdateError("Failed to link dataframe to dashboard: No results from database")
            
            # Get the dashboard and update its timestamp
            dashboard = Dashboard.inflate(results[0][0])
            dashboard.updated_at = datetime.utcnow().isoformat()
            dashboard.save()
            
            self.logger.info(f"Dataframe {dataframe_id} added to dashboard {dashboard_id} successfully")
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error adding dataframe to dashboard: {str(e)}")
            raise DashboardUpdateError(f"Failed to add dataframe to dashboard: {str(e)}")
    
    def create_dataframe_and_add_to_dashboard(
        self,
        dashboard_id: str,
        user_id: str,
        content: str,
        columns: str,
        metadata: str = "{}",
        message_id: Optional[str] = None
    ) -> Tuple[Dashboard, Dataframe]:
        """
        Create a dataframe and add it to a dashboard in a single transaction
        
        Args:
            dashboard_id: The dashboard's unique ID
            user_id: User ID requesting the operation
            content: JSON string containing dataframe content
            columns: JSON string defining column structure
            metadata: Optional metadata as JSON string
            message_id: Optional ID of the message that triggered this creation
            
        Returns:
            Tuple of (Updated Dashboard entity, Created Dataframe entity)
            
        Raises:
            DataframeCreationError: If the dataframe cannot be created
            DashboardUpdateError: If the dashboard relationship cannot be created
        """
        # Start a transaction
        results = None
        dataframe = None
        
        try:
            # Create the dataframe entity
            dataframe = Dataframe.create_dataframe(
                user_id=user_id,
                content=content,
                columns=columns,
                metadata=metadata,
                message_id=message_id
            )
            
            self.logger.info(f"Dataframe created with ID: {dataframe.dataframe_id}")
            
            # Add the dataframe to the dashboard
            dashboard = self.add_dataframe_to_dashboard(dashboard_id, dataframe.dataframe_id)
            
            return dashboard, dataframe
            
        except Exception as e:
            # If there's any error and we created a dataframe, delete it
            if dataframe is not None:
                try:
                    dataframe.delete()
                except:
                    self.logger.error(f"Failed to clean up dataframe {dataframe.dataframe_id} after error")
                    
            self.logger.error(f"Error in create_dataframe_and_add_to_dashboard: {str(e)}")
            raise DataframeCreationError(f"Failed to create dataframe and add to dashboard: {str(e)}")
    
    def remove_dataframe_from_dashboard(
        self,
        dashboard_id: str,
        dataframe_id: str
    ) -> Dashboard:
        """
        Remove a dataframe from a dashboard by deleting the relationship
        
        Args:
            dashboard_id: The dashboard's unique ID
            dataframe_id: The dataframe's unique ID
            
        Returns:
            The updated Dashboard entity
            
        Raises:
            DashboardUpdateError: If the relationship cannot be removed
        """
        try:
            # Create a Cypher query to remove the relationship
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:CONTAINS_DATAFRAME]->(df:Dataframe {dataframe_id: $dataframe_id})
            DELETE r
            RETURN d
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'dataframe_id': dataframe_id
            }
            
            # Execute the query
            results, _ = db.cypher_query(query, params)
            
            if not results or len(results) == 0:
                self.logger.error(f"Failed to remove dataframe {dataframe_id} from dashboard {dashboard_id}")
                raise DashboardUpdateError(f"Failed to remove dataframe from dashboard: No results from database")
            
            # Get the dashboard and update its timestamp
            dashboard = Dashboard.inflate(results[0][0])
            dashboard.updated_at = datetime.utcnow().isoformat()
            dashboard.save()
            
            self.logger.info(f"Dataframe {dataframe_id} removed from dashboard {dashboard_id} successfully")
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error removing dataframe from dashboard: {str(e)}")
            raise DashboardUpdateError(f"Failed to remove dataframe from dashboard: {str(e)}")
