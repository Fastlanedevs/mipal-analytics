#!/usr/bin/env python
import asyncio
import time
import logging
import json
from omegaconf import OmegaConf
from cmd_server.server.container import create_container
from app.analytics.repository.analytics_repository import AnalyticsRepository
from app.pal.analytics.adapters.analytics_repository_adapter import AnalyticsRepositoryAdapter

# Configure logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

async def test_get_database_schema_performance(analytics_repository: AnalyticsRepository, database_uid: str) -> None:
    """
    Test the performance of get_database_schema_from_neo4j function.
    
    Args:
        analytics_repository: AnalyticsRepository instance
        database_uid: The UID of the database to retrieve schema for
    """
    logger.info(f"Starting performance test for analytics_repository.get_database_schema_from_neo4j with database_uid: {database_uid}")
    
    # Run the function and measure execution time
    start_time = time.time()
    try:
        schema = await analytics_repository.get_database_schema_from_neo4j(database_uid)
        execution_time = time.time() - start_time
        
        # Log performance results
        logger.info(f"Schema retrieval completed in {execution_time:.2f} seconds")
        logger.info(f"Schema: {schema}")
        return schema
        
            
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error retrieving schema: {str(e)}")
        logger.error(f"Failed after {execution_time:.2f} seconds")
        return None

async def test_adapter_get_schema_performance(adapter: AnalyticsRepositoryAdapter, database_uid: str) -> None:
    """
    Test the performance of AnalyticsRepositoryAdapter's get_schema function.
    
    Args:
        adapter: AnalyticsRepositoryAdapter instance
        database_uid: The UID of the database to retrieve schema for
    """
    logger.info(f"Starting performance test for analytics_repository_adapter.get_schema with database_uid: {database_uid}")
    
    # Run the function and measure execution time
    start_time = time.time()
    try:
        schema = await adapter.get_schema(database_uid)
        execution_time = time.time() - start_time
        
        # Log performance results
        logger.info(f"Adapter schema retrieval completed in {execution_time:.2f} seconds")
        logger.info(f"Schema for adapter: {schema.dict()}")

        return schema
        
            
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Error retrieving schema from adapter: {str(e)}")
        logger.error(f"Failed after {execution_time:.2f} seconds")
        return None

def compare_schema_results(repo_schema, adapter_schema):
    """
    Compare the results from both schema retrieval methods.
    
    Args:
        repo_schema: Schema from analytics_repository.get_database_schema_from_neo4j
        adapter_schema: Schema from analytics_repository_adapter.get_schema
    """
    if not repo_schema or not adapter_schema:
        logger.warning("Cannot compare schema results: at least one schema is missing")
        return
    
    logger.info("Comparing schema results:")
    
    # Compare table counts
    repo_table_count = len(repo_schema.get('tables', []))
    adapter_table_count = len(adapter_schema.tables)
    logger.info(f"Table count comparison: Repository: {repo_table_count}, Adapter: {adapter_table_count}")
    
    # Compare first table if available
    if repo_schema.get('tables') and adapter_schema.tables:
        repo_first_table = repo_schema['tables'][0]
        adapter_first_table = adapter_schema.tables[0]
        
        # Compare columns count
        repo_column_count = len(repo_first_table.get('columns', []))
        adapter_column_count = len(adapter_first_table.columns) if hasattr(adapter_first_table, 'columns') else 0
        logger.info(f"First table column count: Repository: {repo_column_count}, Adapter: {adapter_column_count}")
    
    # Compare relationship data
    repo_relationships = repo_schema.get('relationships', [])
    repo_relationship_count = len(repo_relationships)
    
    adapter_relationship_count = 0
    for table in adapter_schema.tables:
        if hasattr(table, 'relationships') and table.relationships:
            adapter_relationship_count += len(table.relationships)
    
    logger.info(f"Relationship count: Repository: {repo_relationship_count}, Adapter: {adapter_relationship_count}")
    
    logger.info("Schema comparison completed")

async def main():
    """Main entry point for the performance testing script."""
    try:
        # Load configuration
        logger.info("Loading configuration...")
        config = OmegaConf.load("conf/config.yaml")
        
        # Initialize container with dependencies
        logger.info("Initializing dependency container...")
        container = create_container(cfg=config)
        
        # Get the AnalyticsRepository from the container
        analytics_repository = container.analytics_repository()
        
        # Create the AnalyticsRepositoryAdapter
        analytics_repository_adapter = container.analytics_repository_adapter()

        analytics_service = container.analytics_service()
        
        # Mock database_uid - replace with actual value when running the test
        database_uid = "daaf8e66b5d94e33bf2f29b6f1e669de"  # Replace this with a real database UID
        table_uid = "7ba2ce586a1f4a3e964564406c453dab"
        await analytics_service.get_recommendations(database_uid, table_uid)
        
    except Exception as e:
        logger.error(f"Error in main function: {str(e)}")

if __name__ == "__main__":
    asyncio.run(main())
