from sqlalchemy import Column, String, DateTime, Integer, Text, JSON, ForeignKey, Boolean
from sqlalchemy.dialects.postgresql import UUID, JSONB
from sqlalchemy.sql import func
import uuid
from datetime import datetime, timezone
import json

from pkg.db_util.sql_alchemy.declarative_base import Base
from app.chat.entity.chat import Role


class ConversationModel(Base):
    __tablename__ = "conversations"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    user_id = Column(String, nullable=False, index=True)
    name = Column(String, nullable=False, default="New Conversation")
    model = Column(String,  nullable=True, index=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), index=True)
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_activity_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    current_leaf_message_id = Column(UUID(as_uuid=True), nullable=True)
    meta_data = Column(JSONB, nullable=True)
    
    def to_entity(self):
        from app.chat.entity.chat import Conversation
        
        return Conversation(
            id=self.id,
            user_id=self.user_id,
            name=self.name,
            model=self.model,
            created_at=self.created_at,
            updated_at=self.updated_at,
            last_activity=self.last_activity_at,
            current_leaf_message_id=self.current_leaf_message_id,
            meta_data=self.meta_data,
            messages=[]  # Messages will be added separately
        )
    
    @staticmethod
    def from_entity(entity):
        return ConversationModel(
            id=entity.id,
            user_id=entity.user_id,
            name=entity.name,
            model=entity.model,
            created_at=entity.created_at,
            updated_at=entity.updated_at,
            last_activity_at=entity.last_activity,
            current_leaf_message_id=entity.current_leaf_message_id,
            meta_data=entity.meta_data
        )


def serialize_datetime(obj: dict) -> dict:
    """
    Recursively convert datetime objects in a dictionary to ISO format strings.
    Also convert UUID objects to strings to ensure JSON serializability.
    
    Args:
        obj: Dictionary that might contain datetime objects or UUID objects
        
    Returns:
        dict: Dictionary with datetime and UUID objects converted to strings
    """
    if isinstance(obj, dict):
        return {k: serialize_datetime(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [serialize_datetime(item) for item in obj]
    elif isinstance(obj, datetime):
        return obj.isoformat()
    elif isinstance(obj, uuid.UUID):
        return str(obj)
    else:
        return obj


class MessageModel(Base):
    __tablename__ = "messages"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey("conversations.id"), nullable=False, index=True)
    parent_message_id = Column(UUID(as_uuid=True), nullable=True, index=True)
    role = Column(String, nullable=False)
    content = Column(Text, nullable=True)
    model = Column(String, nullable=True)
    index = Column(Integer, nullable=False, default=0)
    stop_reason = Column(String, nullable=True)
    database_uid = Column(String, nullable=True)
    table_uid = Column(String, nullable=True)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    
    # Rich content
    documents = Column(JSONB, nullable=True)
    codes = Column(JSONB, nullable=True)
    artifacts = Column(JSONB, nullable=True)
    attachments = Column(JSONB, nullable=True)
    references = Column(JSONB, nullable=True)
    suggestions = Column(JSONB, nullable=True)
    files = Column(JSONB, nullable=True)
    meta_data = Column(JSONB, nullable=True)
    
    def to_entity(self):
        from app.chat.entity.chat import (
            Message, Document, CodeSnippet, Role, Artifact, 
            Attachment, Suggestion, File, Reference,
        )
        
        # Parse JSON fields to their respective objects
        documents_list = []
        if self.documents:
            documents_list = [Document(**doc) for doc in self.documents]
            
        codes_list = []
        if self.codes:
            codes_list = [CodeSnippet(**code) for code in self.codes]
            
        artifacts_list = []
        if self.artifacts:
            artifacts_list = [Artifact(**artifact) for artifact in self.artifacts]
            
        attachments_list = []
        if self.attachments:
            attachments_list = [Attachment(**attachment) for attachment in self.attachments]
            
        references_list = []
        if self.references:
            references_list = [Reference(**ref) for ref in self.references]
            
        suggestions_list = []
        if self.suggestions:
            suggestions_list = [Suggestion(**suggestion) for suggestion in self.suggestions]
            
        files_list = []
        if self.files:
            files_list = [File(**file) for file in self.files]
        
        return Message(
            id=self.id,
            conversation_id=self.conversation_id,
            parent_message_id=self.parent_message_id,
            role=Role(self.role),
            content=self.content,
            model=self.model,
            index=self.index,
            stop_reason=self.stop_reason,
            database_uid=self.database_uid,
            table_uid=self.table_uid,
            created_at=self.created_at,
            documents=documents_list,
            codes=codes_list,
            artifacts=artifacts_list,
            attachments=attachments_list,
            references=references_list,
            suggestions=suggestions_list,
            files=files_list,
            meta_data=self.meta_data or {}
        )
    
    @staticmethod
    def from_entity(entity):
        # Convert entity lists to dictionaries for JSON storage
        documents = [serialize_datetime(doc.dict()) for doc in entity.documents] if entity.documents else None
        codes = [serialize_datetime(code.dict()) for code in entity.codes] if entity.codes else None
        artifacts = [serialize_datetime(artifact.dict()) for artifact in entity.artifacts] if entity.artifacts else None
        attachments = [serialize_datetime(attachment.dict()) for attachment in entity.attachments] if entity.attachments else None
        references = [serialize_datetime(ref.dict()) for ref in entity.references] if entity.references else None
        suggestions = [serialize_datetime(suggestion.dict()) for suggestion in entity.suggestions] if entity.suggestions else None
        files = [serialize_datetime(file.dict()) for file in entity.files] if entity.files else None
        meta_data = serialize_datetime(entity.meta_data) if entity.meta_data else None
        
        return MessageModel(
            id=entity.id,
            conversation_id=entity.conversation_id,
            parent_message_id=entity.parent_message_id,
            role=entity.role.value,
            content=entity.content,
            model=entity.model,
            index=entity.index,
            stop_reason=entity.stop_reason,
            database_uid=entity.database_uid,
            table_uid=entity.table_uid,
            created_at=entity.created_at,
            documents=documents,
            codes=codes,
            artifacts=artifacts,
            attachments=attachments,
            references=references,
            suggestions=suggestions,
            files=files,
            meta_data=meta_data
        )


class ChartModel(Base):
    __tablename__ = "charts"
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4, index=True)
    title = Column(String, nullable=True)
    description = Column(Text, nullable=True)
    chart_type = Column(String, nullable=False)
    chart_schema = Column(JSONB, nullable=False)
    chart_data = Column(JSONB, nullable=False)
    created_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    updated_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc), onupdate=lambda: datetime.now(timezone.utc))
    last_refreshed_at = Column(DateTime(timezone=True), nullable=False, default=lambda: datetime.now(timezone.utc))
    created_by = Column(String, nullable=False, index=True)
    org_id = Column(String, nullable=True, index=True)
    visibility = Column(String, nullable=False, default="PRIVATE")
    
    # Reference to the message that generated this chart
    message_id = Column(UUID(as_uuid=True), nullable=True, index=True)
