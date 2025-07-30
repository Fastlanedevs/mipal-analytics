import uuid
from uuid import UUID
from datetime import datetime, timezone
from typing import Any, List, Dict, Optional
from enum import Enum
from pydantic import BaseModel, Field, ConfigDict




class ProcessingStatus(str, Enum):
    """Enum representing the processing status of a document"""
    PROCESSING = "PROCESSING"  # Document is pending processing
    FAILED = "FAILED"  # Document processing failed
    SUCCESS = "SUCCESS"  # Document processing succeeded

class DocumentStatus(str, Enum):
    """Enum representing the status of a document"""
    META_DATA_FETCHED = "META_DATA_FETCHED"         # Document is pending processing
    CONTENT_FETCHED = "CONTENT_FETCHED" # Document is currently being processed
    CHUNKING_SUCCEEDED = "CHUNKING_SUCCEEDED" # Document has been chunked
    EMBEDDING_SUCCEEDED = "EMBEDDING_SUCCEEDED" # Document has been embedded
    ENTITY_RELATION_EXTRACTION_SUCCEEDED = "ENTITY_EXTRACTION_SUCCEEDED" # Document has been processed
    COMPLETED = "COMPLETED"  # Successfully processed




class IntegrationType(str, Enum):
    """Enum representing different integration services"""

    GOOGLE_CALENDAR = "GOOGLE_CALENDAR"
    GOOGLE_DRIVE = "GOOGLE_DRIVE"
    GOOGLE_GMAIL = "GOOGLE_GMAIL"
    MICROSOFT_TEAMS = "MICROSOFT_TEAMS"
    MICROSOFT_ONEDRIVE = "MICROSOFT_ONEDRIVE"
    MICROSOFT_OUTLOOK = "MICROSOFT_OUTLOOK"
    MICROSOFT_CALENDER = "MICROSOFT_CALENDER"
    SLACK_CHAT = "SLACK_CHAT"
    POSTGRESQL = "POSTGRESQL"

    @classmethod
    def get_all_integration_types(cls) -> list:
        return [integration_type for integration_type in cls]


class UserIntegration(BaseModel):
    """Entity representing a user's integration"""

    integration_id: UUID
    user_id: str
    integration_type: IntegrationType
    credential: Dict[str, Any] | None = None
    expires_at: datetime | None = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    settings: Dict[str, Any] | None = None
    is_active: bool = True


class SyncIntegration(BaseModel):
    """Entity for tracking integration synchronization status"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True
    )

    user_id: str
    integration_id: UUID
    status: str
    integration_type: str
    sync_id: UUID
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    completed_at: Optional[datetime] = None
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    error_message: Optional[str] = None
    credentials: Optional[Dict[str, Any]] = None


class UserDocument(BaseModel):
    """Entity representing user's documents for knowledge base"""
    model_config = ConfigDict(
        arbitrary_types_allowed=True,
        populate_by_name=True
    )

    id: UUID = Field(default_factory=lambda: uuid.uuid4())
    user_id: str
    address: Optional[str] = None
    original_file_id: str
    source_type: str
    integration_id: UUID
    file_name: str
    file_type: str
    size: Optional[int] = None
    content: Optional[str] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    status: DocumentStatus  # Kept for backward compatibility/general status, use processing_status for detailed stage
    processing_status: ProcessingStatus
    error: Optional[str] = None
    chunks_count: Optional[int] = None
    entities_count: Optional[int] = None
    relationships_count: Optional[int] = None
    doc_metadata: Optional[Dict[str, Any]] = None



class DocumentTextChunk(BaseModel):

    id: UUID
    user_id: str
    document_id: UUID
    content: str
    content_vector: Optional[List[float]] = None
    chunk_order_index: int = 0
    start_position: int = 0
    end_position: int = 0
    tokens: int = 0
    chunk_type: str = "paragraph"  # paragraph, section, semantic
    content_hash: Optional[str] = None  # SHA-256 hash for deduplication
    address: Optional[str] = None
    meta_data: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class DocumentEntity(BaseModel):
    """Entity representing a named entity extracted from document text"""

    id: UUID
    user_id: str
    entity_name: str
    entity_type: str
    description: Optional[str] = None
    confidence: float = 0.5
    keys: List[str] = Field(default_factory=list)  # For retrieval
    value: str = ""  # Summarized value for retrieval
    global_themes: List[str] = Field(default_factory=list)  # High-level themes

    source_chunks: List[UUID] = Field(default_factory=list)
    document_id: UUID
    source_slices: List[int] = Field(default_factory=list)  # Track which text slices
    occurrence_count: int = 1  # How many times entity appears

    entity_vector: Optional[List[float]] = None
    pagerank_score: Optional[float] = None
    betweenness_centrality: Optional[float] = None
    community_id: Optional[int] = None
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class EntityRelationship(BaseModel):

    id: UUID
    user_id: str
    source_entity_id: UUID
    target_entity_id: UUID
    relationship_type: str
    description: Optional[str] = None
    keywords: List[str] = Field(default_factory=list)
    # LightRAG enhancements
    strength: float = 1.0  # Relationship strength (0-1)
    confidence: float = 0.5  # Extraction confidence
    keys: List[str] = Field(default_factory=list)  # For retrieval
    value: str = ""  # Summarized value for retrieval
    global_themes: List[str] = Field(default_factory=list)  # High-level themes
    # Source tracking
    source_chunks: List[UUID] = Field(default_factory=list)
    document_id: UUID
    source_slices: List[int] = Field(default_factory=list)
    occurrence_count: int = 1

    # Vector embeddings
    relationship_vector: Optional[List[float]] = None

    # Bidirectional flag
    is_bidirectional: bool = False

    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class KeyValuePair(BaseModel):
    """LLM profiling result - key-value pairs for retrieval"""
    key: str
    value: str
    entity_name: Optional[str] = None
    is_global_key: bool = False

class QueryType(Enum):
    """Query classification for dual-level retrieval"""
    SPECIFIC = "specific"  # Detail-oriented, specific entities
    ABSTRACT = "abstract"  # Conceptual, broader topics
    HYBRID = "hybrid"     # Combination of both


class RetrievalResult(BaseModel):
    """Model for knowledge retrieval results using the LightRAG Mix technique"""
    chunks: List[DocumentTextChunk] = Field(default_factory=list)
    entities: List[DocumentEntity] = Field(default_factory=list)
    relationships: List[EntityRelationship] = Field(default_factory=list)
    query: str | None = None
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Additional metadata
    total_chunks_found: int | None = None
    total_entities_found: int | None = None
    total_relationships_found: int | None = None
    execution_time_ms: float | None = None
    retrieval_strategy: str = "mix"  # Can be "mix", "vector", "graph", etc.

