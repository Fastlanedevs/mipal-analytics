from datetime import datetime
from typing import Any, Optional

from pydantic import BaseModel, Field
from uuid import UUID

class Person(BaseModel):
    Name: str
    image: str
    Position: str
    Role: str


class Document(BaseModel):
    title: str
    type: str
    uploaded_by: str | None
    source_url: str | None


class CodeSnippet(BaseModel):
    type: str
    title: str
    content: str
    language: str | None = None


class Artifact(BaseModel):
    artifact_type: str
    content: str
    language: str | None = None
    title: str | None = None
    file_type: str | None = None


class Attachment(BaseModel):
    file_name: str
    file_size: int
    file_type: str
    extracted_content: str


class SuggestionContent(BaseModel):
    title: str = ""
    type: str = ""
    source_url: str | None = ""
    uploaded_by: str = ""
    description: str = ""
    text: str = ""


class Suggestion(BaseModel):
    type: str
    suggestion_content: SuggestionContent


class FileDTO(BaseModel):
    id: UUID
    title: str
    content: str
    address: str | None


class Reference(BaseModel):
    type: str
    title: str
    content: str | None
    address: str | None


class MessageDTO(BaseModel):
    id: UUID
    role: str
    content: str
    conversation_id: UUID
    parent_message_id: Optional[UUID] = None
    model: str | None = None
    database_uid: str | None = None
    table_uid: str | None = None
    suggestions: list[Suggestion] = []
    people: list[Person] = []
    documents: list[Document] = []
    references: list[Reference] = []
    follow_up_questions: list[str] = []
    skip_option: bool = False
    codes: list[CodeSnippet] = []
    artifacts: list[Artifact] = []
    attachments: list[Attachment] = []
    files: list[FileDTO] = []
    edited_at: str = ""
    edited_by: str = ""
    regenerating: bool = False
    original_content: list[str] = []
    stop_reason: str | None = None
    stop_sequence: str | None = None
    created_at: datetime
    index: int
    truncated: bool = False
    sender: str
    metadata: dict[str, Any] = Field(default_factory=dict)


class CreateConversationResponse(BaseModel):
    id: UUID
    name: str
    model: str | None = None
    created_at: datetime
    updated_at: datetime
    is_starred: bool = False
    current_leaf_message_id: UUID | None = None


class GetConversationResponse(BaseModel):
    id: UUID
    name: str
    model: str | None = None
    created_at: datetime
    updated_at: datetime
    is_starred: bool = False
    current_leaf_message_id: UUID | None = None
    chat_messages: list[MessageDTO]


# Request DTOs
class CreateConversationRequest(BaseModel):
    id: UUID
    model: str | None = Field(None, description="Model identifier")


class CompletionRequest(BaseModel):
    prompt: str
    parent_message_id: Optional[UUID]  = None
    attachments: list[Attachment] = []
    files: list[FileDTO] = []
    web_search: bool = False
    knowledge_search: bool = False
    selected_suggestions: list[Suggestion] = []
    rendering_mode: str = Field(
        "messages", description="Rendering mode for the response"
    )
    sync_sources: list[str] = []
    timezone: str = Field("UTC", description="User's timezone")
    model: str | None = None
    database_uid: str | None = None
    table_uid: str | None = None


class ConversationDTO(BaseModel):
    id: UUID
    name: str
    model: str | None
    created_at: datetime
    updated_at: datetime
    is_starred: bool = False
    current_leaf_message_id: UUID | None = None


class ListConversationsResponse(BaseModel):
    conversations: list[ConversationDTO]


# Error responses


class FileExtractRequest(BaseModel):
    file_content: bytes
    file_name: str
    mime_type: str | None = None


class FileExtractResponse(BaseModel):
    extracted_content: str
    file_name: str
    file_type: str
    file_size: int


class PAL(BaseModel):
    id: str
    name: str
    pal_enum: str
    description: str
    type: str
    is_active: bool
    image: str = ""
    suggestions: list[str] = []
