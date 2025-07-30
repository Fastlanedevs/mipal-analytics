"""
Neo4j database schema module.

This is the main entry point for the schema module, providing access
to all models and services for database schema management.
"""
import uuid
from datetime import datetime
from typing import Optional, Dict, List, Any
from fastapi import HTTPException

# Re-export all models
from app.analytics.repository.schema.models import (
    ForeignKeyRel, 
    SharedColumnRel,
    Column,
    Table,
    Database
)

# Re-export database credential models
from app.analytics.repository.schema.models.database import (
    DatabaseCredential,
    DatabaseIntegrationStatus
)

# Re-export all services
from app.analytics.repository.schema.services import (
    infer_foreign_key_relationships
)

# Re-export utility functions
from app.analytics.repository.schema.utils import (
    singular_form,
    plural_form
)

# Set up a logger for this module
from pkg.log.logger import get_logger
logger = get_logger('schema')

# Import for type hints
from app.analytics.entity.analytics import DatabaseType

# Define the get_or_create_database function
async def get_or_create_database(
    name: str,
    description: str,
    db_type: str,
    user_id: str,
    integration_id: str
) -> Database:
    """Get or create a database node"""
    try:
        #REVIEW - It should be based on integration_id and user_id if we want to support multiple databases with the same name
        # Check if database exists for this user (using both name and user_id)
        database = Database.nodes.get(name=name, user_id=user_id)
        
        # Convert db_type to string value if it's an enum
        if isinstance(db_type, DatabaseType):
            db_type = db_type.value
        
        # Check if database type matches
        if database.type != db_type:
            raise HTTPException(
                status_code=400,
                detail=f"Database '{name}' exists but is not a {db_type} database"
            )
        
        # Update description if provided
        if description:
            database.description = description
            database.save()
        
        return database
        
    except Database.DoesNotExist:
        now = datetime.utcnow().isoformat()
        
        # Convert db_type to string value if it's an enum
        if isinstance(db_type, DatabaseType):
            db_type = db_type.value
            
        database = Database(
            name=name,
            type=db_type,  # Store as string value
            description=description or "",
            integration_id=integration_id, # Either mapped to integration id or created a new one
            user_id=user_id,
            unique_key=f"{user_id}:{name}",  # Create compound unique key
            created_at=now,
            updated_at=now,
            is_active=True,
            is_deleted=False
        ).save()
        
        return database
