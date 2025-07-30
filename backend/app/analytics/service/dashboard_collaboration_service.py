import logging
from typing import Dict, List, Any, Optional
from datetime import datetime

from app.middleware.auth import TokenData
from app.analytics.repository.schema.models.dashboard import Dashboard
from app.analytics.errors import (
    DashboardNotFoundError,
    DashboardAccessDeniedError,
    DashboardUpdateError
)
from app.analytics.service.dashboard_service import DashboardService
from pkg.log.logger import Logger

class DashboardCollaborationService:
    """Service for dashboard collaboration and access control"""
    
    def __init__(self, logger: Logger, dashboard_service: DashboardService):
        """
        Initialize the dashboard collaboration service
        
        Args:
            logger: Optional logger instance
        """
        self.logger = logger
        self.dashboard_service = dashboard_service
    
    async def share_with_users(
        self,
        dashboard_id: str,
        requested_user_id: str,
        user_access_list: List[Dict[str, str]]  # [{user_id: str, permission: str}]
    ) -> Dashboard:
        """
        Share a dashboard with specific users
        
        Args:
            dashboard_id: The dashboard's unique ID
            token_data: User authentication token data
            user_access_list: List of user IDs and their permission levels
            
        Returns:
            The updated Dashboard entity
        """
        # Get the dashboard service
        dashboard_service = self.dashboard_service
        
        # Get the dashboard (this will verify ownership)
        dashboard = await dashboard_service.get_dashboard(dashboard_id, requested_user_id)
        
        # Only owner can share the dashboard
        if dashboard.user_id != requested_user_id:
            self.logger.error(f"User {requested_user_id} doesn't have permission to share dashboard {dashboard_id}")
            raise DashboardAccessDeniedError("Only the dashboard owner can share the dashboard")
        
        try:
            # Use Cypher to efficiently create/update multiple relationships
            from neomodel import db
            
            for access in user_access_list:
                user_id = access['user_id']
                permission = access['permission']
                
                if user_id == requested_user_id:
                    # Skip if trying to share with self (owner always has full access)
                    continue
                
                # Validate permission
                if permission not in ["view", "edit"]:
                    raise ValueError(f"Invalid permission: {permission}. Must be 'view' or 'edit'")
                
                # Create or update sharing relationship with Cypher
                query = """
                MATCH (d:Dashboard {dashboard_id: $dashboard_id})
                MATCH (u:User {uid: $user_id})
                MERGE (d)-[r:SHARED_WITH]->(u)
                SET r.permission = $permission,
                    r.granted_at = $granted_at
                RETURN d, r, u
                """
                
                params = {
                    'dashboard_id': dashboard_id,
                    'user_id': user_id,
                    'permission': permission,
                    'granted_at': datetime.utcnow().isoformat()
                }
                
                results, _ = db.cypher_query(query, params)
                
                if not results or len(results) == 0:
                    self.logger.error(f"Failed to share dashboard {dashboard_id} with user {user_id}")
                    raise DashboardUpdateError(f"Failed to share dashboard with user {user_id}")
            
            # Update the dashboard's updated_at timestamp
            dashboard.updated_at = datetime.utcnow().isoformat()
            dashboard.save()
            
            self.logger.info(f"Dashboard {dashboard_id} shared successfully with {len(user_access_list)} users")
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error sharing dashboard: {str(e)}")
            raise DashboardUpdateError(f"Failed to share dashboard: {str(e)}")
    
    async def remove_user_access(
        self,
        dashboard_id: str,
        requested_user_id: str,
        user_id: str
    ) -> Dashboard:
        """
        Remove a user's access to a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            token_data: User authentication token data
            user_id: ID of the user whose access should be removed
            
        Returns:
            The updated Dashboard entity
        """
        # Get the dashboard service
        dashboard_service = self.dashboard_service
        
        # Get the dashboard (this will verify access)
        dashboard = await dashboard_service.get_dashboard(dashboard_id, user_id)
        
        # Only owner can manage access
        if dashboard.user_id != user_id:
            self.logger.error(f"User {user_id} doesn't have permission to manage dashboard access")
            raise DashboardAccessDeniedError("Only the dashboard owner can manage access")
        
        try:
            # Use Cypher to delete the relationship
            from neomodel import db
            
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:SHARED_WITH]->(u:User {uid: $user_id})
            DELETE r
            RETURN d
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'user_id': requested_user_id
            }
            
            results, _ = db.cypher_query(query, params)
            
            # Update the dashboard's updated_at timestamp
            dashboard.updated_at = datetime.utcnow().isoformat()
            dashboard.save()
            
            self.logger.info(f"Access for user {requested_user_id} to dashboard {dashboard_id} removed successfully")
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error removing user access: {str(e)}")
            raise DashboardUpdateError(f"Failed to remove user access: {str(e)}")
    
    async def update_user_permission(
        self,
        dashboard_id: str,
        requested_user_id: str,
        user_id: str,
        permission: str
    ) -> Dashboard:
        """
        Update a user's permission level for a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            token_data: User authentication token data
            user_id: ID of the user whose permission should be updated
            permission: New permission level ("view" or "edit")
            
        Returns:
            The updated Dashboard entity
        """
        # Get the dashboard service
        dashboard_service = self.dashboard_service
        
        # Get the dashboard (this will verify access)
        dashboard = await dashboard_service.get_dashboard(dashboard_id, requested_user_id)
        
        # Only owner can update permissions
        if dashboard.user_id != requested_user_id:
            self.logger.error(f"User {requested_user_id} doesn't have permission to update dashboard permissions")
            raise DashboardAccessDeniedError("Only the dashboard owner can update permissions")
        
        # Validate permission
        if permission not in ["view", "edit"]:
            raise ValueError(f"Invalid permission: {permission}. Must be 'view' or 'edit'")
        
        try:
            # Use Cypher to update the relationship
            from neomodel import db
            
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:SHARED_WITH]->(u:User {uid: $user_id})
            SET r.permission = $permission
            RETURN d, r, u
            """
            
            params = {
                'dashboard_id': dashboard_id,
                'user_id': requested_user_id,
                'permission': permission
            }
            
            results, _ = db.cypher_query(query, params)
            
            if not results or len(results) == 0:
                self.logger.error(f"User {requested_user_id} does not have access to dashboard {dashboard_id}")
                raise DashboardUpdateError(f"User {requested_user_id} does not have access to this dashboard")
            
            # Update the dashboard's updated_at timestamp
            dashboard.updated_at = datetime.utcnow().isoformat()
            dashboard.save()
            
            self.logger.info(f"Permission for user {requested_user_id} on dashboard {dashboard_id} updated to {permission}")
            return dashboard
            
        except Exception as e:
            self.logger.error(f"Error updating user permission: {str(e)}")
            raise DashboardUpdateError(f"Failed to update user permission: {str(e)}")
    
    async def get_dashboard_access(
        self,
        dashboard_id: str,
        requested_user_id: str
    ) -> List[Dict[str, str]]:
        """
        Get list of users with access to a dashboard
        
        Args:
            dashboard_id: The dashboard's unique ID
            token_data: User authentication token data
            
        Returns:
            List of user access details
        """
        # Get the dashboard service
        dashboard_service = self.dashboard_service
        
        # Get the dashboard (this will verify access)
        dashboard = await dashboard_service.get_dashboard(dashboard_id, requested_user_id)
        
        # Only owner can view sharing settings
        if dashboard.user_id != requested_user_id:
            self.logger.error(f"User {requested_user_id} doesn't have permission to view dashboard sharing settings")
            raise DashboardAccessDeniedError("Only the dashboard owner can view sharing settings")
        
        try:
            # Use Cypher to get all SHARED_WITH relationships
            from neomodel import db
            
            query = """
            MATCH (d:Dashboard {dashboard_id: $dashboard_id})-[r:SHARED_WITH]->(u:User)
            RETURN u.uid as user_id, r.permission as permission
            """
            
            params = {
                'dashboard_id': dashboard_id
            }
            
            results, _ = db.cypher_query(query, params)
            
            user_access_list = []
            for record in results:
                user_access_list.append({
                    'user_id': record[0],
                    'permission': record[1]
                })
            
            return user_access_list
            
        except Exception as e:
            self.logger.error(f"Error getting dashboard access: {str(e)}")
            raise DashboardUpdateError(f"Failed to get dashboard access: {str(e)}") 