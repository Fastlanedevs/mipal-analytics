from typing import Any, Literal, Optional

from pydantic import BaseModel

from app.chat.api.dto import Artifact, Suggestion, Reference
from uuid import UUID

class MessageMetadata(BaseModel):
    id: str
    type: Literal["message"]
    role: Literal["assistant"]
    model: str
    parent_uuid: UUID | None = None
    uuid: UUID
    content: list[Any] = []
    stop_reason: str | None = None
    stop_sequence: str | None = None


class MessageStartEvent(BaseModel):
    type: Literal["message_start"]
    message: MessageMetadata


class ContentBlock(BaseModel):
    type: Literal["text"]
    text: str


class ContentBlockStartEvent(BaseModel):
    type: Literal["content_block_start"]
    index: int
    content_block: ContentBlock


class TextDelta(BaseModel):
    type: Literal["text_delta"]
    text: str


class ContentBlockDeltaEvent(BaseModel):
    type: Literal["content_block_delta"]
    index: int
    delta: TextDelta


class ContentBlockStopEvent(BaseModel):
    type: Literal["content_block_stop"]
    index: int


class MessageDeltaData(BaseModel):
    stop_reason: str
    stop_sequence: str | None = None


class MessageDeltaEvent(BaseModel):
    type: Literal["message_delta"]
    delta: MessageDeltaData


class MessageStopEvent(BaseModel):
    type: Literal["message_stop"]


class ErrorData(BaseModel):
    message: str
    type: str


class ErrorEvent(BaseModel):
    type: Literal["error"]
    error: ErrorData


class MessageLimit(BaseModel):
    type: Literal["within_limit"]
    resetsAt: str | None = None
    remaining: int | None = None
    perModelLimit: int | None = None


class MessageLimitEvent(BaseModel):
    type: Literal["message_limit"]
    message_limit: MessageLimit


class StopResponseResult(BaseModel):
    stop_id: UUID


class SuggestionBlock(BaseModel):
    type: Literal["suggestions"] = "suggestions"
    suggestions: list[Suggestion]


class SuggestionBlockStartEvent(BaseModel):
    type: Literal["suggestion_block_start"] = "suggestion_block_start"
    index: int
    suggestion_block: SuggestionBlock


class SuggestionBlockStopEvent(BaseModel):
    type: Literal["suggestion_block_stop"] = "suggestion_block_stop"
    index: int


class ArtifactBlock(BaseModel):
    type: Literal["artifacts"] = "artifacts"
    artifacts: list[Artifact]


class ArtifactBlockStartEvent(BaseModel):
    type: Literal["artifact_block_start"] = "artifact_block_start"
    index: int
    artifact_block: ArtifactBlock


class ArtifactBlockStopEvent(BaseModel):
    type: Literal["artifact_block_stop"] = "artifact_block_stop"
    index: int


class ReferenceBlock(BaseModel):
    type: Literal["references"] = "references"
    references: list[Reference]


class ReferenceBlockStartEvent(BaseModel):
    type: Literal["reference_block_start"] = "reference_block_start"
    index: int
    reference_block: ReferenceBlock


class ReferenceBlockStopEvent(BaseModel):
    type: Literal["reference_block_stop"] = "reference_block_stop"
    index: int


class MetaContent(BaseModel):
    id: str
    title: str
    status: str
    type: str
    description: list[dict] = []


class MetaContentEvent(BaseModel):
    type: Literal["meta_content"] = "meta_content"
    index: Optional[int] = None
    meta_content: MetaContent


class DataSummaryDeltaEvent(BaseModel):
    type: Literal["data_summary_delta"] = "data_summary_delta"
    delta: dict
