from neomodel import (
    StructuredNode, 
    StringProperty, 
    UniqueIdProperty,
    BooleanProperty
)
from datetime import datetime
import uuid


class Dataframe(StructuredNode):
    """Model for dataframe entities in the database"""
    
    # Unique identifier
    dataframe_id = UniqueIdProperty()  # UniqueIdProperty generates its own UUID
    
    # Core dataframe data
    content = StringProperty(required=True)  # JSON string of dataframe content
    columns = StringProperty(required=True)  # JSON string of column definitions
    metadata = StringProperty(default="{}")  # Additional metadata
    
    # Ownership and tracking
    user_id = StringProperty(required=True)
    message_id = StringProperty()  # ID of the message that triggered this dataframe creation
    
    # Timestamps
    created_at = StringProperty(default=lambda: datetime.utcnow().isoformat())
    updated_at = StringProperty(default=lambda: datetime.utcnow().isoformat())
    is_deleted = BooleanProperty(default=False)
    
    @classmethod
    def create_dataframe(cls, content, columns, user_id, metadata=None, message_id=None):
        """
        Create a new dataframe
        
        Args:
            content: JSON string of dataframe content
            columns: JSON string of column definitions
            user_id: Owner's user ID
            metadata: Optional metadata as JSON string
            message_id: Optional ID of the message that triggered this creation
            
        Returns:
            The created Dataframe instance
        """
        dataframe = cls(
            content=content,
            columns=columns,
            user_id=user_id,
            metadata=metadata or "{}",
            message_id=message_id,
            created_at=datetime.utcnow().isoformat(),
            updated_at=datetime.utcnow().isoformat()
        )
        dataframe.save()
        return dataframe
    
    # Used to update the dataframe content
    def update(self, content=None, columns=None, metadata=None):
        """
        Update dataframe properties
        
        Args:
            content: Optional new content
            columns: Optional new columns
            metadata: Optional new metadata
            
        Returns:
            The updated dataframe
        """
        if content is not None:
            self.content = content
        
        if columns is not None:
            self.columns = columns
            
        if metadata is not None:
            self.metadata = metadata
            
        self.updated_at = datetime.utcnow().isoformat()
        self.save()
        return self
        
    def delete(self):
        """
        Permanently delete the dataframe from the database
        """
        self.cypher("MATCH (df:Dataframe {dataframe_id: $self.dataframe_id}) DETACH DELETE df")
        
    def soft_delete(self):
        """
        Mark the dataframe as deleted without removing it from the database
        """
        self.is_deleted = True
        self.updated_at = datetime.utcnow().isoformat()
        self.save()
        
    def restore(self):
        """
        Restore a soft-deleted dataframe
        """
        self.is_deleted = False
        self.updated_at = datetime.utcnow().isoformat()
        self.save()