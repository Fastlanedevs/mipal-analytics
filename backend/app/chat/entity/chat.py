from pydantic import BaseModel, Field, field_validator
from datetime import datetime, timezone
from typing import List, Optional, Dict, Any, Union
from enum import Enum
from pydantic.dataclasses import dataclass
import uuid
from uuid import UUID


class Role(str, Enum):
    """Enum for message roles"""
    ASSISTANT = "assistant"
    USER = "user"
    SYSTEM = "system"


class Person(BaseModel):
    Name: str
    image: str
    Position: str
    Role: str


class Document(BaseModel):
    """Document meta_data and content"""
    id: UUID
    title: str
    type: str
    content: Optional[str] = None
    uploaded_by: Optional[str] = None
    source_url: Optional[str] = None


class Attachment(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    type: str
    extracted_content: str
    file_size: int
    embedding: Optional[List[float]] = None
    is_embedded: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class CodeSnippet(BaseModel):
    """Code snippet with metadata"""
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    content: str
    language: Optional[str] = None
    embedding: Optional[List[float]] = None
    is_embedded: bool = False
    metadata: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class Artifact(BaseModel):
    artifact_type: str
    content: str
    language: Optional[str] = None
    title: Optional[str] = None
    file_type: Optional[str] = None
    embedding: Optional[List[float]] = None
    is_embedded: bool = False


class SuggestionContent(BaseModel):
    title: str = ""
    type: str = ""
    source_url: Optional[str] = None
    uploaded_by: str = ""
    description: str = ""
    text: str = ""


class Suggestion(BaseModel):
    type: str
    suggestion_content: SuggestionContent


class File(BaseModel):
    id: UUID
    title: str
    content: str
    address: Optional[str] = None


class Reference(BaseModel):
    type: str
    title: str
    content: Optional[str] = None
    address: Optional[str] = None


class KnowledgeResponse(BaseModel):
    """Structured output for the KnowledgePAL agent that can include text content and/or references"""
    content: Optional[str] = None
    references: List[Reference] = Field(default_factory=list)
    type: str = "knowledge_response"

    @property
    def has_content(self) -> bool:
        return self.content is not None and len(self.content) > 0

    @property
    def has_references(self) -> bool:
        return len(self.references) > 0


class Message(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    conversation_id: UUID
    parent_message_id: Optional[UUID] = None
    index: int = 0
    role: Role
    content: str
    model: Optional[str] = None
    # Database fields for analytics
    database_uid: Optional[str] = None
    table_uid: Optional[str] = None

    # Rich content
    suggestions: List[Suggestion] = Field(default_factory=list)
    references: List[Reference] = Field(default_factory=list)
    people: List[Person] = Field(default_factory=list)
    documents: List[Document] = Field(default_factory=list)
    codes: List[CodeSnippet] = Field(default_factory=list)
    artifacts: List[Artifact] = Field(default_factory=list)
    attachments: List[Attachment] = Field(default_factory=list)
    files: List[File] = Field(default_factory=list)
    follow_up_questions: List[str] = Field(default_factory=list)
    current_leaf_message_id: Optional[UUID] = None

    stop_reason: Optional[str] = None
    stop_sequence: Optional[str] = None

    meta_data: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    @field_validator("parent_message_id", mode="before")
    def ensure_parent_message_id(cls, v):
        # Return None for empty values
        if not v:
            return None
        # If string was passed, convert to UUID
        if isinstance(v, str) and v:
            return UUID(v)
        return v


class Conversation(BaseModel):
    id: UUID = Field(default_factory=uuid.uuid4)
    user_id: str
    name: str = "New Conversation"
    model: Optional[str] = None
    messages: List[Message] = Field(default_factory=list)

    # State
    current_leaf_message_id: Optional[UUID] = None
    last_activity: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Vector search

    # meta_data
    meta_data: Dict[str, Any] = Field(default_factory=dict)
    is_starred: bool = False
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    def add_message(self, message: Message) -> None:
        """Add message and update conversation stats"""
        self.messages.append(message)
        self.updated_at = datetime.now(timezone.utc)


class CompletionRequest(BaseModel):
    prompt: str
    parent_message_id: Optional[UUID] = None
    attachments: List[Attachment] = Field(default_factory=list)
    files: List[File] = Field(default_factory=list)
    selected_suggestions: List[Suggestion] = Field(default_factory=list)
    rendering_mode: str = Field(
        "messages", description="Rendering mode for the response"
    )
    sync_sources: List[str] = Field(default_factory=list)
    timezone: str = Field("UTC", description="User's timezone")
    model: Optional[str] = None
    web_search: bool = False
    knowledge_search: bool = False
    database_uid: Optional[str] = None
    table_uid: Optional[str] = None


class FileExtract(BaseModel):
    file_name: str
    file_size: int
    file_type: str
    extracted_content: str


class PALAnalyticsResponse(BaseModel):
    response: str
    suggestions: List[str] = Field(default_factory=list)

