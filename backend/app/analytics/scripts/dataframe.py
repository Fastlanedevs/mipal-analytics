#!/usr/bin/env python
import asyncio
import logging
import json
import uuid
from datetime import datetime
from omegaconf import OmegaConf
from cmd_server.server.container import create_container
from app.analytics.service.dashboard_service import DashboardService

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def add_dataframe_to_dashboard(dashboard_service: DashboardService, 
                                   dashboard_id: str, 
                                   user_id: str 
                                   ) -> dict:
    """
    Add a dataframe to a dashboard
    
    Args:
        dashboard_service: DashboardService instance
        dashboard_id: Dashboard ID
        user_id: User ID
        
    Returns:
        dict: Contains the dashboard and dataframe objects
    """
    logger.info(f"Adding dataframe to dashboard {dashboard_id}")
    
    # Create sample dataframe content
    content = json.dumps({
        "rows": [
            {"id": 1, "name": "John", "age": 25, "city": "New York"},
            {"id": 2, "name": "Jane", "age": 30, "city": "Boston"},
            {"id": 3, "name": "Bob", "age": 35, "city": "Chicago"},
            {"id": 4, "name": "Alice", "age": 28, "city": "San Francisco"},
            {"id": 5, "name": "Dave", "age": 32, "city": "Seattle"}
        ]
    })
    
    # Create sample columns definition
    columns = json.dumps([
        {"name": "id", "type": "number", "label": "ID"},
        {"name": "name", "type": "string", "label": "Name"},
        {"name": "age", "type": "number", "label": "Age"},
        {"name": "city", "type": "string", "label": "City"}
    ])
    
    # Create sample metadata
    metadata = json.dumps({
        "title": "Sample User Data",
        "description": "A test dataframe with user information",
        "created_at": datetime.now().isoformat()
    })
    
    try:
        # Add dataframe to dashboard
        dashboard, dataframe = await dashboard_service.add_dataframe_to_dashboard(
            dashboard_id=dashboard_id,
            requested_user_id=user_id,
            content=content,
            columns=columns,
            metadata=metadata
        )
        
        logger.info(f"Successfully added dataframe {dataframe.dataframe_id} to dashboard {dashboard_id}")
        logger.info(f"Dataframe content sample (truncated): {content[:100]}...")
        logger.info(f"Dataframe columns: {columns}")
        
        return {"dashboard": dashboard, "dataframe": dataframe}
        
    except Exception as e:
        logger.error(f"Error adding dataframe to dashboard: {str(e)}")
        raise

async def remove_dataframe_from_dashboard(dashboard_service: DashboardService, 
                                        dashboard_id: str, 
                                        dataframe_id: str,
                                        user_id: str 
                                        ) -> dict:
    """
    Remove a dataframe from a dashboard
    
    Args:
        dashboard_service: DashboardService instance
        dashboard_id: Dashboard ID
        dataframe_id: Dataframe ID to remove
        user_id: User ID
        
    Returns:
        dict: Contains the updated dashboard object
    """
    logger.info(f"Removing dataframe {dataframe_id} from dashboard {dashboard_id}")
    
    try:
        # Remove the dataframe from the dashboard
        updated_dashboard = await dashboard_service.remove_dataframe_from_dashboard(
            dashboard_id=dashboard_id,
            dataframe_id=dataframe_id,
            requested_user_id=user_id
        )
        
        logger.info(f"Successfully removed dataframe {dataframe_id} from dashboard {dashboard_id}")
        
        return {"dashboard": updated_dashboard}
        
    except Exception as e:
        logger.error(f"Error removing dataframe from dashboard: {str(e)}")
        raise

async def main():
    """Main entry point for the dataframe testing script."""
    try:
        config = OmegaConf.load("conf/config.yaml")
        
        container = create_container(cfg=config)
        
        # Get the DashboardService from the container
        db_conn = container.db_conn()
        dashboard_service = container.dashboard_service()
        
        # Test user and org IDs - replace with actual values
        user_id = "d63d687ef15d4941b72c2a1866e371a8"  # Replace with a real user ID in production
        dashboard_id = "0ad4b71b3cd842f8a3f2c2e66d3d947d"
        
        # Example of how to use the separated functions
        # Uncomment the function call you want to execute
        
        # Add a dataframe to the dashboard
        result = await add_dataframe_to_dashboard(dashboard_service, dashboard_id, user_id)
        
        # If you want to remove the dataframe, use the dataframe_id from the add operation
        # await remove_dataframe_from_dashboard(dashboard_service, dashboard_id, "db446cbf843c491aaffe58cf2260143a", user_id)
        
        logger.info("Operation completed successfully")
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
