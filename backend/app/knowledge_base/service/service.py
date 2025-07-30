import uuid
from uuid import UUID
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from app.knowledge_base.entity.entity import (
    UserDocument, SyncIntegration, UserIntegration,
    RetrievalResult, DocumentTextChunk, DocumentEntity,
    EntityRelationship
)
from app.knowledge_base.entity.gsuite_entity import GoogleFileMetadata
from pkg.util.file_content_extractor import ExtractedContent



# Define service interfaces
class ILLMAdapter(ABC):
    """Interface for Language Model operations"""

    @abstractmethod
    async def generate_embedding(self, user_id: str, text: str) -> Union[List[float], None]:
        """Generate embeddings for text"""
        pass

    @abstractmethod
    async def generate_multiple_embeddings(self, user_id: str, texts: List[str]) -> Union[List[List[float]], None]:
        """Generate embeddings for multiple texts"""
        pass

    @abstractmethod
    async def generate_image_analysis(self, user_id: str, image_base64: str) -> Union[str, None]:
        """Analyze image content"""
        pass


    @abstractmethod
    async def extract_entities(self, user_id: str, text: str) -> Dict[str, Any]:
        """Extract entities and relationships from text"""
        pass

    @abstractmethod
    async def extract_keywords(self, user_id: str, text: str) -> Dict[str, List[str]]:
        """Extract high-level and low-level keywords from text"""
        pass

    @abstractmethod
    async def make_key_values(self, node_text: str, user_id: str) -> Dict[str, Any]:
        pass

    @abstractmethod
    async def generate_global_themes(self, user_id: str, relationships: List[Dict[str, Any]]) -> Dict[str, List[str]]:
        pass



class IKnowledgeBaseRepository(ABC):
    """Interface for Knowledge Base Repository with LightRAG Mix technique support"""

    # Document Management
    @abstractmethod
    async def create_document(self, document: UserDocument) -> UserDocument:
        pass

    @abstractmethod
    async def get_document_by_id(self, document_id: UUID, user_id: str) -> Optional[UserDocument]:
        pass

    @abstractmethod
    async def get_document_by_original_id(self, user_id: str, original_file_id: str) -> Optional[UserDocument]:
        pass

    @abstractmethod
    async def update_document(self, document: UserDocument) -> UserDocument:
        pass

    # Chunk Management
    @abstractmethod
    async def create_text_chunks(self, chunks: List[DocumentTextChunk]) -> List[DocumentTextChunk]:
        pass

    @abstractmethod
    async def get_text_chunks_by_ids(self, chunk_ids: List[UUID]) -> List[DocumentTextChunk]:
        pass

    # Entity Management
    @abstractmethod
    async def create_entities(self, entities: List[DocumentEntity]) -> List[DocumentEntity]:
        pass

    @abstractmethod
    async def get_entities_by_name(self, entity_name: str, user_id: str) -> List[DocumentEntity]:
        pass

    @abstractmethod
    async def get_entity_by_id(self, entity_id: UUID, user_id: str) -> Optional[DocumentEntity]:
        pass

    # Relationship Management
    @abstractmethod
    async def create_relationships(self, relationships: List[EntityRelationship]) -> List[EntityRelationship]:
        pass

    @abstractmethod
    async def get_relationships_by_entity_id(self, entity_id: UUID) -> List[EntityRelationship]:
        pass

    @abstractmethod
    async def get_relationships_for_entities(self, entity_ids: List[UUID]) -> List[EntityRelationship]:
        pass

    # Vector Search Methods
    @abstractmethod
    async def vector_search_chunks(self, query_vector: List[float], user_id: str, top_k: int = 10,
                                   similarity_threshold: Optional[float] = None) -> List[DocumentTextChunk]:
        pass

    @abstractmethod
    async def vector_search_entities(self, query_vector: List[float], user_id: str, top_k: int = 10,
                                     similarity_threshold: Optional[float] = None) -> List[DocumentEntity]:
        pass

    @abstractmethod
    async def vector_search_relationships(self, query_vector: List[float], user_id: str, top_k: int = 10,
                                          similarity_threshold: Optional[float] = None) -> List[EntityRelationship]:
        pass

    @abstractmethod
    async def rank_chunks_by_vector_and_keywords(self, chunks: List[DocumentTextChunk], query_embedding: List[float],
                                                 high_level_keywords: List[str], low_level_keywords: List[str],
                                                 top_k: int, user_id: str) -> List[DocumentTextChunk]:
        pass

    # Document Search Methods
    @abstractmethod
    async def search_documents_by_prefix(self, user_id: str, prefix: str) -> List[UserDocument]:
        pass

    @abstractmethod
    async def search_relevant_documents_word_based(self, user_id: str, query: str) -> List[UserDocument]:
        pass


class IIntegrationAdapter(ABC):
    @abstractmethod
    async def get_sync_integration(self, user_id: str, sync_id: UUID) -> SyncIntegration:
        pass

    @abstractmethod
    async def update_sync_status(
            self, user_id: str, sync_id: UUID, status: str, error_message: Optional[str] = None) -> None:
        pass

    @abstractmethod
    async def get_integration(self, user_id: str, integration_id: UUID) -> UserIntegration:
        pass

    @abstractmethod
    async def get_latest_checkpoint_integration(self, user_id: str, integration_id: UUID) -> Optional[str]:
        pass

    @abstractmethod
    async def update_latest_checkpoint_integration(self, user_id: str, integration_id: UUID, checkpoint: str) -> bool:
        pass


class IGSuiteAdapter(ABC):
    @abstractmethod
    def make_oauth_token(self, credentials: dict):
        pass

    @abstractmethod
    async def get_all_documents(self, oauth_token: Any,
                                modified_after: Optional[datetime]) -> list[GoogleFileMetadata]:
        pass

    @abstractmethod
    async def extract_document_content(self, oauth_token: Any, metadata: GoogleFileMetadata) -> ExtractedContent:
        pass

    @abstractmethod
    async def get_checkpoint_drive_token(self, oauth_token: Any) -> str:
        pass

    @abstractmethod
    async def get_changed_documents(self, oauth_token: Any,
                                    start_page_token: str) -> Tuple[List[GoogleFileMetadata], List[str], str]:
        pass



class IKnowledgeIngestionService(ABC):
    """Interface for knowledge ingestion services"""

    @abstractmethod
    async def sync_integration(self, user_id: str, sync_id: UUID) -> dict[str, int]:
        pass


class IKnowledgeRetrievalService(ABC):
    """Interface for Knowledge Retrieval Service operations"""

    @abstractmethod
    async def retrieve_knowledge(self, user_id: str, query: str,
                                 retrieval_mode: str = "lightrag",
                                 max_results: int = 10,
                                 enable_reranking: bool = True) -> RetrievalResult:
        """
        Retrieve knowledge using specified strategy

        Args:
            user_id: User ID
            query: User query
            retrieval_mode: Retrieval mode - "naive" (vector only), "mix" (hybrid), "kg" (knowledge graph)
            vector_similarity_threshold: Minimum similarity score for vector results
            max_results: Maximum number of results to return

        Returns:
            RetrievalResult with chunks, entities, and relationships
        """
        pass


    @abstractmethod
    async def search_documents_by_prefix(self, user_id: str, prefix: str) -> list[UserDocument]:
        """Search documents by prefix"""
        pass

    @abstractmethod
    async def search_relevant_documents_word_based(self, user_id: str, query: str) -> list[UserDocument]:
        """Search for relevant documents using word-based search"""
        pass

    @abstractmethod
    async def get_document_info(self, user_id: str, document_id: UUID) -> Optional[UserDocument]:
        """Get basic document information without content for reference display"""
        pass
