from datetime import datetime
from typing import Optional
from pydantic import BaseModel, Field


class DataframeBase(BaseModel):
    """Base class for dataframe models"""
    content: str = Field(..., description="JSON string containing dataframe content")
    columns: str = Field(..., description="JSON string defining column structure")
    metadata: str = Field("{}", description="Additional metadata as JSON string")


class Dataframe(DataframeBase):
    """Dataframe entity model"""
    dataframe_id: str
    user_id: str  # ID of the user who created the dataframe
    message_id: Optional[str] = None  # ID of the message that triggered this dataframe creation
    created_at: datetime
    updated_at: datetime
    is_deleted: bool = False

    @classmethod
    def from_db_model(cls, db_model):
        """
        Convert a database model to an entity model
        
        Args:
            db_model: Database model instance
            
        Returns:
            Dataframe entity
        """
        return cls(
            dataframe_id=db_model.dataframe_id,
            content=db_model.content,
            columns=db_model.columns,
            metadata=db_model.metadata,
            user_id=db_model.user_id,
            message_id=db_model.message_id,
            created_at=datetime.fromisoformat(db_model.created_at),
            updated_at=datetime.fromisoformat(db_model.updated_at),
            is_deleted=db_model.is_deleted
        )
