from typing import List, Optional, Dict, Any, Tuple, Union
import uuid
from uuid import UUID
from datetime import datetime, timezone
import json
import numpy as np
import hashlib
from sqlalchemy import create_engine, select, update, delete, and_, or_, func, text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from pkg.db_util.postgres_conn import PostgresConnection

from app.knowledge_base.entity.entity import (
    UserDocument,
    DocumentTextChunk,
    DocumentEntity,
    EntityRelationship,
    DocumentStatus,
    ProcessingStatus
)
from app.knowledge_base.repository.sql_schema.user_documents import (
    UserDocuments as UserDocumentsModel,
    DocumentTextChunks as DocumentTextChunksModel,
    DocumentEntity as DocumentEntityModel,
    DocumentEntitiesRelationship,
    EntityKeyValues,
    GlobalThemes,
    LLMResponseCache,
    QueryHistory
)
from app.knowledge_base.service.service import IKnowledgeBaseRepository
from pkg.log.logger import Logger
from sqlalchemy.exc import SQLAlchemyError
import re


def compute_md5hash_id(content: str, prefix: str = "") -> str:
    """Generate a unique MD5 hash ID with optional prefix."""
    return prefix + hashlib.md5(content.encode()).hexdigest()


# ========================================
# CONVERSION FUNCTIONS - COMPLETED
# ========================================

def model_document_db_to_entity(document: UserDocumentsModel) -> UserDocument:
    """Convert SQL document model to entity"""
    return UserDocument(
        id=document.id,
        user_id=document.user_id,
        address=document.address,
        original_file_id=document.original_file_id,
        source_type=document.source_type,
        integration_id=document.integration_id,
        file_name=document.file_name,
        file_type=document.file_type,
        size=document.size,
        content=document.content,
        created_at=document.created_at,
        updated_at=document.updated_at,
        status=DocumentStatus(document.status) if document.status else DocumentStatus.META_DATA_FETCHED,
        processing_status=ProcessingStatus(
            document.processing_status) if document.processing_status else ProcessingStatus.PROCESSING,
        error=document.error,
        chunks_count=document.chunks_count,
        entities_count=getattr(document, 'entities_count', None),
        relationships_count=getattr(document, 'relationships_count', None),
        doc_metadata=document.doc_metadata or {}
    )


def model_text_chunk_db_to_entity(chunk: DocumentTextChunksModel) -> DocumentTextChunk:
    """Convert SQL text chunk model to entity"""

    return DocumentTextChunk(
        id=chunk.id,
        user_id=chunk.user_id,
        document_id=chunk.document_id,
        content=chunk.content,
        content_vector=chunk.content_vector,
        content_hash=getattr(chunk, 'content_hash', None),
        chunk_type=getattr(chunk, 'chunk_type', 'paragraph'),
        chunk_order_index=chunk.chunk_order_index,
        start_position=getattr(chunk, 'start_position', 0),
        end_position=getattr(chunk, 'end_position', 0),
        tokens=chunk.tokens,
        address=chunk.address,
        meta_data=getattr(chunk, 'meta_data', None),
        created_at=chunk.created_at
    )


def model_entity_db_to_entity(entity: DocumentEntityModel) -> DocumentEntity:
    """Convert SQL entity model to entity object"""
    # Handle entity_vector conversion
    entity_vector = None
    if hasattr(entity, 'entity_vector') and entity.entity_vector is not None:
        if isinstance(entity.entity_vector, (list, np.ndarray)):
            entity_vector = list(entity.entity_vector)
        elif isinstance(entity.entity_vector, str):
            try:
                entity_vector = json.loads(entity.entity_vector)
            except json.JSONDecodeError:
                entity_vector = None

    # Handle source_chunks conversion
    source_chunks = []
    if hasattr(entity, 'source_chunks') and entity.source_chunks:
        if isinstance(entity.source_chunks, list):
            source_chunks = [UUID(chunk_id) if isinstance(chunk_id, str) else chunk_id for chunk_id in
                             entity.source_chunks]
        elif isinstance(entity.source_chunks, str):
            try:
                source_chunks_data = json.loads(entity.source_chunks)
                source_chunks = [UUID(chunk_id) for chunk_id in source_chunks_data]
            except (json.JSONDecodeError, ValueError):
                source_chunks = []

    # Handle keys conversion
    keys = []
    if hasattr(entity, 'keys') and entity.keys:
        if isinstance(entity.keys, list):
            keys = entity.keys
        elif isinstance(entity.keys, str):
            try:
                keys = json.loads(entity.keys)
            except json.JSONDecodeError:
                keys = [entity.keys]  # Single key as string

    # Handle global_themes conversion
    global_themes = []
    if hasattr(entity, 'global_themes') and entity.global_themes:
        if isinstance(entity.global_themes, list):
            global_themes = entity.global_themes
        elif isinstance(entity.global_themes, str):
            try:
                global_themes = json.loads(entity.global_themes)
            except json.JSONDecodeError:
                global_themes = []

    return DocumentEntity(
        id=entity.id,
        user_id=entity.user_id,
        entity_name=entity.entity_name,
        entity_type=entity.entity_type,
        description=entity.description or "",
        confidence=getattr(entity, 'confidence', 0.5),
        keys=keys,
        value=getattr(entity, 'value', entity.description or ""),
        global_themes=global_themes,
        source_chunks=source_chunks,
        document_id=entity.document_id,
        source_slices=getattr(entity, 'source_slices', []),
        occurrence_count=getattr(entity, 'occurrence_count', 1),
        entity_vector=entity_vector,
        pagerank_score=getattr(entity, 'pagerank_score', None),
        betweenness_centrality=getattr(entity, 'betweenness_centrality', None),
        community_id=getattr(entity, 'community_id', None),
        created_at=entity.created_at
    )


def model_relationship_db_to_entity(relationship: DocumentEntitiesRelationship) -> EntityRelationship:
    """Convert SQL relationship model to entity object"""
    # Handle relationship_vector conversion
    relationship_vector = None
    if hasattr(relationship, 'relationship_vector') and relationship.relationship_vector is not None:
        if isinstance(relationship.relationship_vector, (list, np.ndarray)):
            relationship_vector = list(relationship.relationship_vector)
        elif isinstance(relationship.relationship_vector, str):
            try:
                relationship_vector = json.loads(relationship.relationship_vector)
            except json.JSONDecodeError:
                relationship_vector = None

    # Handle keywords conversion
    keywords = []
    if relationship.keywords:
        if isinstance(relationship.keywords, list):
            keywords = relationship.keywords
        elif isinstance(relationship.keywords, str):
            try:
                keywords = json.loads(relationship.keywords)
            except json.JSONDecodeError:
                # If it's not JSON, split by comma
                keywords = [k.strip() for k in relationship.keywords.split(",") if k.strip()]

    # Handle source_chunks conversion
    source_chunks = []
    if hasattr(relationship, 'source_chunks') and relationship.source_chunks:
        if isinstance(relationship.source_chunks, list):
            source_chunks = [UUID(chunk_id) if isinstance(chunk_id, str) else chunk_id for chunk_id in
                             relationship.source_chunks]
        elif isinstance(relationship.source_chunks, str):
            try:
                source_chunks_data = json.loads(relationship.source_chunks)
                source_chunks = [UUID(chunk_id) for chunk_id in source_chunks_data]
            except (json.JSONDecodeError, ValueError):
                source_chunks = []

    # Handle keys and global_themes
    keys = []
    if hasattr(relationship, 'keys') and relationship.keys:
        if isinstance(relationship.keys, list):
            keys = relationship.keys
        elif isinstance(relationship.keys, str):
            try:
                keys = json.loads(relationship.keys)
            except json.JSONDecodeError:
                keys = [relationship.keys]

    global_themes = []
    if hasattr(relationship, 'global_themes') and relationship.global_themes:
        if isinstance(relationship.global_themes, list):
            global_themes = relationship.global_themes
        elif isinstance(relationship.global_themes, str):
            try:
                global_themes = json.loads(relationship.global_themes)
            except json.JSONDecodeError:
                global_themes = []

    return EntityRelationship(
        id=relationship.id,
        user_id=relationship.user_id,
        source_entity_id=relationship.source_entity_id,
        target_entity_id=relationship.target_entity_id,
        relationship_type=relationship.relationship_type,
        description=relationship.description or "",
        keywords=keywords,
        strength=getattr(relationship, 'strength', relationship.weight if hasattr(relationship, 'weight') else 1.0),
        confidence=getattr(relationship, 'confidence', 0.5),
        keys=keys,
        value=getattr(relationship, 'value', relationship.description or ""),
        global_themes=global_themes,
        source_chunks=source_chunks,
        document_id=relationship.document_id,
        source_slices=getattr(relationship, 'source_slices', []),
        occurrence_count=getattr(relationship, 'occurrence_count', 1),
        relationship_vector=relationship_vector,
        is_bidirectional=getattr(relationship, 'is_bidirectional', False),
        created_at=relationship.created_at
    )


class KnowledgeBaseRepository(IKnowledgeBaseRepository):
    """Repository implementation with LightRAG support"""

    def __init__(self, sql_db_conn: PostgresConnection, logger: Logger):
        self.sql_db_conn = sql_db_conn
        self.logger = logger
        self._indexes_initialized = False

        # Remove the synchronous call - we'll initialize indexes when needed
        # self._initialize_vector_indexes()  # Add vector index initialization

    async def _initialize_vector_indexes(self):
        """Create optimized vector indexes for LightRAG"""
        index_queries = [
            # IVFFlat indexes for development
            """
            CREATE INDEX IF NOT EXISTS idx_chunks_vector_ivfflat
                ON document_text_chunks USING ivfflat (content_vector vector_cosine_ops)
                WITH (lists = 100)
            """,

            # HNSW indexes for production
            """
            CREATE INDEX IF NOT EXISTS idx_entities_vector_hnsw
                ON document_entities USING hnsw (entity_vector vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """,

            """
            CREATE INDEX IF NOT EXISTS idx_relationships_vector_hnsw
                ON document_entities_relationships USING hnsw (relationship_vector vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
            """,

            # Composite indexes
            """
            CREATE INDEX IF NOT EXISTS idx_entities_user_name_type
                ON document_entities (user_id, entity_name, entity_type)
            """,

            # Fixed GIN indexes with proper operator classes
            """
            CREATE INDEX IF NOT EXISTS idx_entities_keys_gin 
                ON document_entities USING gin(keys)
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_entities_high_confidence 
                ON document_entities (user_id, entity_type, pagerank_score) 
                WHERE confidence > 0.7
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_relationships_themes_gin 
                ON document_entities_relationships USING gin(global_themes)
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_relationships_strength_filter 
                ON document_entities_relationships (user_id, relationship_type, strength) 
                WHERE strength > 0.5
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_entities_cross_doc 
                ON document_entities (user_id, entity_name, occurrence_count) 
                WHERE occurrence_count > 1
            """,
            
            # Regular B-tree index instead of GIN for UUID columns
            """
            CREATE INDEX IF NOT EXISTS idx_chunks_user_id 
                ON document_text_chunks (user_id)
            """,
            
            """
            CREATE INDEX IF NOT EXISTS idx_documents_recent 
                ON user_documents (user_id, created_at DESC) 
                WHERE processing_status = 'SUCCESS'
            """
        ]

        successful_indexes = 0
        failed_indexes = 0

        # Create each index in a separate transaction to avoid transaction rollback affecting other indexes
        for i, query in enumerate(index_queries):
            idx_num = i + 1
            try:
                async with self.sql_db_conn.get_session() as session:
                    await session.execute(text(query))
                    await session.commit()
                    successful_indexes += 1
                    self.logger.info(f"Successfully created index {idx_num}/{len(index_queries)}")
            except Exception as idx_e:
                failed_indexes += 1
                self.logger.warning(f"Could not create index {idx_num}: {idx_e}")
                # Continue with other indexes even if one fails

        self.logger.info(f"PostgreSQL vector indexes initialization completed: {successful_indexes} successful, {failed_indexes} failed")
        
        if failed_indexes > 0:
            self.logger.warning(f"Some indexes failed to create ({failed_indexes}/{len(index_queries)}), but repository will continue to function")

    async def create_document(self, document: UserDocument) -> UserDocument:
        """Create a new user document in the database"""
        self.logger.info(f"create_document: starting id={document.id}, user_id={document.user_id}")
        try:
            async with self.sql_db_conn.get_session() as session:
                # Generate UUID if not provided
                if not document.id:
                    document.id = uuid.uuid4()

                new_doc = UserDocumentsModel(
                    id=document.id,
                    user_id=document.user_id,
                    address=document.address,
                    original_file_id=document.original_file_id,
                    source_type=document.source_type,
                    integration_id=document.integration_id,
                    file_name=document.file_name,
                    file_type=document.file_type,
                    size=document.size,
                    content=document.content,
                    status=document.status.value if document.status else DocumentStatus.META_DATA_FETCHED.value,
                    processing_status=document.processing_status.value if document.processing_status else ProcessingStatus.PROCESSING.value,
                    error=document.error,
                    chunks_count=document.chunks_count,
                    entities_count=getattr(document, 'entities_count', None),
                    relationships_count=getattr(document, 'relationships_count', None),
                    doc_metadata=document.doc_metadata
                )

                session.add(new_doc)
                await session.commit()
                await session.refresh(new_doc)
                self.logger.info(f"create_document: completed for document id={new_doc.id}")

                return model_document_db_to_entity(new_doc)
        except SQLAlchemyError as e:
            self.logger.error(f"Database error creating document: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error creating document: {str(e)}")
            raise

    async def get_document_by_id(self, document_id: UUID, user_id: str) -> Optional[UserDocument]:
        """Get a document by its ID and user ID"""
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = select(UserDocumentsModel).where(
                    and_(
                        UserDocumentsModel.id == document_id,
                        UserDocumentsModel.user_id == user_id
                    )
                )
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record:
                    return model_document_db_to_entity(record)
                return None
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting document {str(document_id)}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting document {str(document_id)}: {str(e)}")
            raise

    async def get_document_by_original_id(self, user_id: str, original_file_id: str) -> Optional[UserDocument]:
        """Get document by its original file ID"""
        self.logger.info(f"get_document_by_original_id: user_id={user_id}, original_file_id={original_file_id}")
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = select(UserDocumentsModel).where(
                    and_(
                        UserDocumentsModel.original_file_id == original_file_id,
                        UserDocumentsModel.user_id == user_id
                    )
                )
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record:
                    return model_document_db_to_entity(record)
                return None
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting document by original ID {original_file_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting document by original ID {original_file_id}: {str(e)}")
            raise

    async def get_documents_by_user_id(self, user_id: str, limit: int = 100, offset: int = 0) -> List[UserDocument]:
        """Get all documents for a specific user with pagination"""
        self.logger.info(f"get_documents_by_user_id: user_id={user_id}, limit={limit}, offset={offset}")
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = select(UserDocumentsModel).where(
                    UserDocumentsModel.user_id == user_id
                ).order_by(UserDocumentsModel.created_at.desc()).limit(limit).offset(offset)

                result = await session.execute(stmt)
                records = result.scalars().all()

                return [model_document_db_to_entity(doc) for doc in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting documents for user {user_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting documents for user {user_id}: {str(e)}")
            raise

    async def list_documents_by_status(self, user_id: str, status: str) -> List[UserDocument]:
        """List documents by processing status"""
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = select(UserDocumentsModel).where(
                    and_(
                        UserDocumentsModel.user_id == user_id,
                        UserDocumentsModel.processing_status == status
                    )
                )

                result = await session.execute(stmt)
                records = result.scalars().all()

                return [model_document_db_to_entity(doc) for doc in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error listing documents by status {status} for user {user_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error listing documents by status {status} for user {user_id}: {str(e)}")
            raise

    async def get_documents_by_ids(self, doc_ids: list[UUID]) -> list[UserDocument]:
        if not doc_ids:
            return []
        async with self.sql_db_conn.get_session() as session:
            stmt = select(UserDocumentsModel).where(UserDocumentsModel.id.in_(doc_ids))
            res = await session.execute(stmt)
            rows = res.scalars().all()
        return [model_document_db_to_entity(r) for r in rows]

    async def update_document(self, document: UserDocument) -> UserDocument:
        """Update an existing document"""
        self.logger.info(f"update_document: start id={document.id}, user_id={document.user_id}")
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = update(UserDocumentsModel).where(
                    and_(
                        UserDocumentsModel.id == document.id,
                        UserDocumentsModel.user_id == document.user_id
                    )
                ).values(
                    address=document.address,
                    file_name=document.file_name,
                    content=document.content,
                    updated_at=datetime.now(tz=timezone.utc),
                    status=document.status.value if document.status else DocumentStatus.META_DATA_FETCHED.value,
                    processing_status=document.processing_status.value if document.processing_status else ProcessingStatus.PROCESSING.value,
                    error=document.error,
                    chunks_count=document.chunks_count,
                    entities_count=getattr(document, 'entities_count', None),
                    relationships_count=getattr(document, 'relationships_count', None),
                    doc_metadata=document.doc_metadata
                )

                await session.execute(stmt)
                await session.commit()

                # Fetch updated document
                return await self.get_document_by_id(document.id, document.user_id)
        except SQLAlchemyError as e:
            self.logger.error(f"Database error updating document {document.id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error updating document {document.id}: {str(e)}")
            raise

    # ==================== Chunk Management ====================

    async def create_text_chunks(self, chunks: list[DocumentTextChunk]) -> list[DocumentTextChunk]:
        """Create or update multiple text chunks for a document using batch processing (upsert)."""
        self.logger.info(f"create_text_chunks (upsert): starting with {len(chunks)} chunks")
        if not chunks:
            return []

        # Initialize vector indexes if not already done
        if not self._indexes_initialized:
            await self._initialize_vector_indexes()
            self._indexes_initialized = True

        try:
            async with self.sql_db_conn.get_session() as session:
                rows_to_upsert = []
                for ch_entity in chunks:
                    if not ch_entity.id:
                        self.logger.warning(
                            f"Chunk missing ID during create_text_chunks: doc_id={ch_entity.document_id}, order={ch_entity.chunk_order_index}. Generating one.")
                        ch_entity.id = uuid.uuid4()

                    # Serialize content_vector if it exists
                    content_vector = None
                    if ch_entity.content_vector:
                        if isinstance(ch_entity.content_vector, (list, np.ndarray)):
                            content_vector = list(ch_entity.content_vector)

                    row_data = dict(
                        id=ch_entity.id,
                        document_id=ch_entity.document_id,
                        content=ch_entity.content,
                        content_hash=ch_entity.content_hash,
                        chunk_type=getattr(ch_entity, 'chunk_type', 'paragraph'),
                        chunk_order_index=ch_entity.chunk_order_index,
                        start_position=ch_entity.start_position,
                        end_position=ch_entity.end_position,
                        tokens=ch_entity.tokens,
                        address=ch_entity.address,
                        content_vector=content_vector,
                        user_id=ch_entity.user_id,
                        meta_data=getattr(ch_entity, 'meta_data', None),
                    )
                    rows_to_upsert.append(row_data)
                    
                    # Log first chunk details for debugging
                    if len(rows_to_upsert) == 1:
                        self.logger.info(f"First chunk data: id={ch_entity.id}, doc_id={ch_entity.document_id}, user_id={ch_entity.user_id}, content_length={len(ch_entity.content)}")

                if not rows_to_upsert:
                    self.logger.info("No valid chunk data to upsert.")
                    return []

                self.logger.info(f"Prepared {len(rows_to_upsert)} rows for upsert")

                # Use PostgreSQL's INSERT ON CONFLICT DO UPDATE for idempotent upsert
                stmt = (
                    insert(DocumentTextChunksModel)
                    .values(rows_to_upsert)
                )
                
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "content": stmt.excluded.content,
                        "content_hash": stmt.excluded.content_hash,
                        "chunk_type": stmt.excluded.chunk_type,
                        "tokens": stmt.excluded.tokens,
                        "address": stmt.excluded.address,
                        "content_vector": stmt.excluded.content_vector,
                        "user_id": stmt.excluded.user_id,
                        "document_id": stmt.excluded.document_id,
                        "chunk_order_index": stmt.excluded.chunk_order_index,
                        "start_position": stmt.excluded.start_position,
                        "end_position": stmt.excluded.end_position,
                        "meta_data": stmt.excluded.meta_data,
                        "updated_at": func.now(),
                    }
                ).returning(DocumentTextChunksModel)

                self.logger.info("Executing upsert statement...")
                persisted_db_chunks = (await session.execute(upsert_stmt)).scalars().all()
                self.logger.info(f"Upsert executed, got {len(persisted_db_chunks)} results")
                
                await session.commit()
                self.logger.info("Transaction committed successfully")

                self.logger.info(f"create_text_chunks (upsert): upserted {len(persisted_db_chunks)} chunks")
                return [model_text_chunk_db_to_entity(db_chunk) for db_chunk in persisted_db_chunks]

        except SQLAlchemyError as e:
            self.logger.error(f"Database error in create_text_chunks (upsert): {str(e)}", exc_info=True)
            raise
        except Exception as e:
            self.logger.error(f"Error creating/updating text chunks: {str(e)}", exc_info=True)
            raise

    async def get_text_chunks_by_document_id(self, document_id: UUID) -> List[DocumentTextChunk]:
        """Get all text chunks for a document"""
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = select(DocumentTextChunksModel).where(
                    DocumentTextChunksModel.document_id == document_id
                ).order_by(DocumentTextChunksModel.chunk_order_index)

                result = await session.execute(stmt)
                records = result.scalars().all()

                return [model_text_chunk_db_to_entity(chunk) for chunk in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting chunks for document {document_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting chunks for document {document_id}: {str(e)}")
            raise

    async def get_text_chunks_by_ids(self, chunk_ids: List[UUID]) -> List[DocumentTextChunk]:
        """Get text chunks by their IDs"""
        if not chunk_ids:
            return []

        try:
            async with self.sql_db_conn.get_session() as session:
                # Process in batches if there are many chunk IDs
                if len(chunk_ids) > 1000:
                    results = []
                    for i in range(0, len(chunk_ids), 1000):
                        batch_ids = chunk_ids[i:i + 1000]
                        stmt = select(DocumentTextChunksModel).where(
                            DocumentTextChunksModel.id.in_(batch_ids)
                        )
                        result = await session.execute(stmt)
                        batch_results = result.scalars().all()
                        results.extend(batch_results)
                else:
                    stmt = select(DocumentTextChunksModel).where(
                        DocumentTextChunksModel.id.in_(chunk_ids)
                    )
                    result = await session.execute(stmt)
                    results = result.scalars().all()

                return [model_text_chunk_db_to_entity(chunk) for chunk in results]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting chunks by IDs: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting chunks by IDs: {str(e)}")
            raise

    async def get_documents_by_processing_status(self, user_id: str, status: ProcessingStatus, limit: int = 100000) -> \
    List[UserDocument]:
        """Get documents for a user based on processing status."""
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = select(UserDocumentsModel).where(
                    and_(
                        UserDocumentsModel.user_id == user_id,
                        UserDocumentsModel.processing_status == status.value
                    )
                ).limit(limit)

                result = await session.execute(stmt)
                records = result.scalars().all()

                return [model_document_db_to_entity(doc) for doc in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting documents by status {status.value} for user {user_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting documents by status {status.value} for user {user_id}: {str(e)}")
            raise

    # ==================== Entity Management ====================

    def _sanitize_array_field(self, field_name: str, field_value: Any, convert_to_str: bool = False) -> List[Any]:
        if field_value is None:
            return []
        
        if callable(field_value):
            self.logger.error(f"Field {field_name} is callable: {type(field_value)}")
            return []
        
        sanitized_value = field_value
        if not isinstance(field_value, (list, tuple)):
            self.logger.warning(f"Field {field_name} is not a list/tuple: {type(field_value)}, attempting to convert to list")
            if hasattr(field_value, '__iter__') and not isinstance(field_value, (str, bytes)):
                try:
                    sanitized_value = list(field_value)
                except Exception as conv_err:
                    self.logger.error(f"Failed to convert iterable {field_name} to list: {conv_err}")
                    return []
            else: # Scalar or str/bytes, wrap it in a list
                sanitized_value = [field_value]
        
        # Ensure all items in the array are proper types
        result = []
        for item in sanitized_value: # Iterate over the now list 'sanitized_value'
            if callable(item):
                self.logger.error(f"Field {field_name} contains callable item: {type(item)}")
                continue
            
            if convert_to_str:
                result.append(str(item))
            else:
                result.append(item)
        
        return result

    async def create_entities(self, entities: list[DocumentEntity]) -> list[DocumentEntity]:
        """Create multiple document entities with optimized batch processing"""
        if not entities:
            self.logger.info("create_entities: No entities provided, returning empty list")
            return []

        # Validate entities before processing - use model_dump() to avoid Pydantic method conflicts
        valid_entities = []
        for entity in entities:
            entity_data = entity.model_dump()
            if not entity_data.get('id'):
                self.logger.warning(f"Entity missing ID: {entity_data.get('entity_name')}, skipping")
                continue
            if not entity_data.get('user_id'):
                self.logger.warning(f"Entity missing user_id: {entity_data.get('id')}, skipping")
                continue
            if not entity_data.get('document_id'):
                self.logger.warning(f"Entity missing document_id: {entity_data.get('id')}, skipping")
                continue
            valid_entities.append(entity)
        
        if not valid_entities:
            self.logger.warning("create_entities: No valid entities after validation, returning empty list")
            return []

        self.logger.info(f"Starting create_entities for {len(valid_entities)} valid entities (filtered from {len(entities)})")

        # Initialize vector indexes if not already done
        if not self._indexes_initialized:
            await self._initialize_vector_indexes()
            self._indexes_initialized = True

        try:
            async with self.sql_db_conn.get_session() as session:
                rows = []
                for i, e in enumerate(valid_entities):
                    try:
                        # Use Pydantic's model_dump() to safely get ALL field values
                        entity_data = e.model_dump()
                        
                        # Additional debugging for first entity
                        if i == 0:
                            self.logger.info(f"Entity {entity_data.get('id')} raw data types:")
                            for key, value in entity_data.items():
                                self.logger.info(f"  {key}: {type(value)} = {repr(value)[:100]}")

                        # Serialize entity_vector separately
                        entity_vector = None
                        entity_vector_raw = entity_data.get('entity_vector')
                        if entity_vector_raw:
                            entity_vector = list(entity_vector_raw) if isinstance(entity_vector_raw, (list, np.ndarray)) else entity_vector_raw

                        # Extract and sanitize ALL fields from the dumped data
                        keys_array = self._sanitize_array_field('keys', entity_data.get('keys'))
                        global_themes_array = self._sanitize_array_field('global_themes', entity_data.get('global_themes'))
                        source_chunks_array = self._sanitize_array_field('source_chunks', entity_data.get('source_chunks'), convert_to_str=True)
                        source_slices_array = self._sanitize_array_field('source_slices', entity_data.get('source_slices'))

                        # Additional debugging for first entity arrays
                        if i == 0:
                            self.logger.info(f"Sanitized arrays:")
                            self.logger.info(f"  keys_array: {type(keys_array)} = {keys_array}")
                            self.logger.info(f"  global_themes_array: {type(global_themes_array)} = {global_themes_array}")
                            self.logger.info(f"  source_chunks_array: {type(source_chunks_array)} = {source_chunks_array}")
                            self.logger.info(f"  source_slices_array: {type(source_slices_array)} = {source_slices_array}")

                        # Build row_data using ONLY dumped data - no direct object access
                        row_data = dict(
                            id=entity_data.get('id'),
                            entity_name=str(entity_data.get('entity_name', '')),
                            entity_type=str(entity_data.get('entity_type', '')),
                            description=str(entity_data.get('description')) if entity_data.get('description') else None,
                            confidence=float(entity_data.get('confidence', 0.5)),
                            keys=keys_array,
                            value=str(entity_data.get('value', '')),
                            global_themes=global_themes_array,
                            source_chunks=source_chunks_array,
                            document_id=entity_data.get('document_id'),
                            user_id=str(entity_data.get('user_id', '')),
                            source_slices=source_slices_array,
                            occurrence_count=int(entity_data.get('occurrence_count', 1)),
                            entity_vector=entity_vector,
                            pagerank_score=float(entity_data.get('pagerank_score')) if entity_data.get('pagerank_score') is not None else None,
                            betweenness_centrality=float(entity_data.get('betweenness_centrality')) if entity_data.get('betweenness_centrality') is not None else None,
                            community_id=int(entity_data.get('community_id')) if entity_data.get('community_id') is not None else None,
                        )
                        
                        # Final validation - check for any callable objects in row_data
                        for field_name, field_value in row_data.items():
                            if callable(field_value):
                                self.logger.error(f"Entity {entity_data.get('id')} row_data field {field_name} is callable: {type(field_value)}")
                                raise ValueError(f"Row data contains callable object in field {field_name}")
                            
                            if isinstance(field_value, list):
                                for j, item in enumerate(field_value):
                                    if callable(item):
                                        self.logger.error(f"Entity {entity_data.get('id')} row_data field {field_name}[{j}] is callable: {type(item)}")
                                        raise ValueError(f"Row data array {field_name} contains callable object at index {j}")

                        rows.append(row_data)
                        
                    except Exception as entity_err:
                        self.logger.error(f"Error processing entity: {entity_err}", exc_info=True)
                        raise  # Re-raise to stop processing

                self.logger.info(f"Prepared {len(rows)} entity rows for upsert")

                # Use PostgreSQL's INSERT ON CONFLICT for idempotent upsert
                stmt = (
                    insert(DocumentEntityModel)
                    .values(rows)
                )
                
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "entity_name": stmt.excluded.entity_name,
                        "entity_type": stmt.excluded.entity_type,
                        "description": stmt.excluded.description,
                        "confidence": stmt.excluded.confidence,
                        "keys": stmt.excluded['keys'],
                        "value": stmt.excluded.value,
                        "global_themes": stmt.excluded.global_themes,
                        "source_chunks": stmt.excluded.source_chunks,
                        "source_slices": stmt.excluded.source_slices,
                        "occurrence_count": stmt.excluded.occurrence_count,
                        "entity_vector": stmt.excluded.entity_vector,
                        "pagerank_score": stmt.excluded.pagerank_score,
                        "betweenness_centrality": stmt.excluded.betweenness_centrality,
                        "community_id": stmt.excluded.community_id,
                        "updated_at": func.now(),
                    },
                ).returning(DocumentEntityModel)

                self.logger.info("Executing entity upsert statement...")
                db_rows = (await session.execute(upsert_stmt)).scalars().all()
                self.logger.info(f"Entity upsert executed, got {len(db_rows)} results")
                
                await session.commit()
                self.logger.info("Entity transaction committed successfully")

                self.logger.info(f"Upserted {len(db_rows)} entities to PostgreSQL")
                return [model_entity_db_to_entity(row) for row in db_rows]

        except Exception as e:
            self.logger.error(f"Error creating entities: {str(e)}", exc_info=True)
            raise

    async def get_entities_by_name(self, entity_name: str, user_id: str) -> List[DocumentEntity]:
        """Get entities by name (optionally filtered by user_id)"""
        try:
            async with self.sql_db_conn.get_session() as session:
                query = select(DocumentEntityModel)

                if user_id:
                    query = query.where(
                        and_(
                            DocumentEntityModel.entity_name == entity_name,
                            DocumentEntityModel.user_id == user_id
                        )
                    )
                else:
                    query = query.where(DocumentEntityModel.entity_name == entity_name)

                result = await session.execute(query)
                records = result.scalars().all()
                return [model_entity_db_to_entity(entity) for entity in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting entities by name {entity_name}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting entities by name {entity_name}: {str(e)}")
            raise

    async def get_entity_by_id(self, entity_id: UUID, user_id: str) -> Optional[DocumentEntity]:
        """Get entity by ID and user ID"""
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = select(DocumentEntityModel).where(
                    and_(
                        DocumentEntityModel.id == entity_id,
                        DocumentEntityModel.user_id == user_id
                    )
                )
                result = await session.execute(stmt)
                record = result.scalar_one_or_none()

                if record:
                    return model_entity_db_to_entity(record)
                return None
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting entity {str(entity_id)}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting entity {str(entity_id)}: {str(e)}")
            raise

    async def delete_entity(self, entity_id: UUID, user_id: str) -> bool:
        """Delete an entity and its relationships"""
        try:
            async with self.sql_db_conn.get_session() as session:
                async with session.begin():
                    # First delete relationships
                    rel_stmt = delete(DocumentEntitiesRelationship).where(
                        or_(
                            DocumentEntitiesRelationship.source_entity_id == entity_id,
                            DocumentEntitiesRelationship.target_entity_id == entity_id
                        )
                    )
                    await session.execute(rel_stmt)

                    # Then delete the entity
                    entity_stmt = delete(DocumentEntityModel).where(
                        and_(
                            DocumentEntityModel.id == entity_id,
                            DocumentEntityModel.user_id == user_id
                        )
                    )
                    result = await session.execute(entity_stmt)
                    return result.rowcount > 0

        except Exception as e:
            self.logger.error(f"Error deleting entity {entity_id}: {str(e)}")
            raise

    # ==================== Relationship Management ====================

    async def create_relationships(self, relationships: list[EntityRelationship]) -> list[EntityRelationship]:
        """Create or update multiple entity relationships with optimized batch processing."""
        if not relationships:
            return []

        self.logger.info(f"create_relationships: input count={len(relationships)}")

        # Filter valid relationships - use model_dump() to avoid Pydantic method conflicts
        valid_relationships = []
        for rel in relationships:
            rel_data = rel.model_dump()
            if (rel_data.get('id') and 
                rel_data.get('source_entity_id') and 
                rel_data.get('target_entity_id') and 
                rel_data.get('user_id')):
                valid_relationships.append(rel)

        if not valid_relationships:
            return []

        # Deduplicate relationships
        unique = {}
        for r in valid_relationships:
            # Use model_dump() to safely access fields for deduplication key
            r_data = r.model_dump()
            key = (r_data.get('source_entity_id'), r_data.get('target_entity_id'), r_data.get('relationship_type') or "RELATED_TO")
            unique.setdefault(key, r)

        payload = list(unique.values())

        try:
            async with self.sql_db_conn.get_session() as session:
                rows = []
                for i, rel in enumerate(payload):
                    try:
                        # Use Pydantic's model_dump() to safely get ALL field values
                        rel_data = rel.model_dump()
                        
                        # Additional debugging for first relationship
                        if i == 0:
                            self.logger.info(f"Relationship {rel_data.get('id')} raw data types:")
                            for key, value in rel_data.items():
                                self.logger.info(f"  {key}: {type(value)} = {repr(value)[:100]}")

                        # Serialize relationship_vector separately
                        relationship_vector = None
                        relationship_vector_raw = rel_data.get('relationship_vector')
                        if relationship_vector_raw:
                            relationship_vector = list(relationship_vector_raw) if isinstance(relationship_vector_raw, (list, np.ndarray)) else relationship_vector_raw

                        # Extract and sanitize ALL fields from the dumped data
                        keywords_array = self._sanitize_array_field('keywords', rel_data.get('keywords'))
                        keys_array = self._sanitize_array_field('keys', rel_data.get('keys'))
                        global_themes_array = self._sanitize_array_field('global_themes', rel_data.get('global_themes'))
                        source_chunks_array = self._sanitize_array_field('source_chunks', rel_data.get('source_chunks'), convert_to_str=True)
                        source_slices_array = self._sanitize_array_field('source_slices', rel_data.get('source_slices'))

                        # Additional debugging for first relationship arrays
                        if i == 0:
                            self.logger.info(f"Sanitized relationship arrays:")
                            self.logger.info(f"  keywords_array: {type(keywords_array)} = {keywords_array}")
                            self.logger.info(f"  keys_array: {type(keys_array)} = {keys_array}")
                            self.logger.info(f"  global_themes_array: {type(global_themes_array)} = {global_themes_array}")
                            self.logger.info(f"  source_chunks_array: {type(source_chunks_array)} = {source_chunks_array}")
                            self.logger.info(f"  source_slices_array: {type(source_slices_array)} = {source_slices_array}")

                        # Build row_data using ONLY dumped data - no direct object access
                        row_data = dict(
                            id=rel_data.get('id'),
                            source_entity_id=rel_data.get('source_entity_id'),
                            target_entity_id=rel_data.get('target_entity_id'),
                            relationship_type=str(rel_data.get('relationship_type', '')),
                            description=str(rel_data.get('description')) if rel_data.get('description') else None,
                            keywords=keywords_array,
                            strength=float(rel_data.get('strength', 1.0)),
                            confidence=float(rel_data.get('confidence', 0.5)),
                            keys=keys_array,
                            value=str(rel_data.get('value', '')),
                            global_themes=global_themes_array,
                            source_chunks=source_chunks_array,
                            document_id=rel_data.get('document_id'),
                            user_id=str(rel_data.get('user_id', '')),
                            source_slices=source_slices_array,
                            occurrence_count=int(rel_data.get('occurrence_count', 1)),
                            relationship_vector=relationship_vector,
                            is_bidirectional=bool(rel_data.get('is_bidirectional', False)),
                            weight=float(rel_data.get('strength', 1.0)),  # Use strength as weight for compatibility
                        )
                        
                        # Final validation - check for any callable objects in row_data
                        for field_name, field_value in row_data.items():
                            if callable(field_value):
                                self.logger.error(f"Relationship {rel_data.get('id')} row_data field {field_name} is callable: {type(field_value)}")
                                raise ValueError(f"Row data contains callable object in field {field_name}")
                            
                            if isinstance(field_value, list):
                                for j, item in enumerate(field_value):
                                    if callable(item):
                                        self.logger.error(f"Relationship {rel_data.get('id')} row_data field {field_name}[{j}] is callable: {type(item)}")
                                        raise ValueError(f"Row data array {field_name} contains callable object at index {j}")

                        rows.append(row_data)
                        
                    except Exception as rel_err:
                        self.logger.error(f"Error processing relationship: {rel_err}", exc_info=True)
                        raise  # Re-raise to stop processing

                self.logger.info(f"Prepared {len(rows)} relationship rows for upsert")

                # Use PostgreSQL's INSERT ON CONFLICT for idempotent upsert
                stmt = (
                    insert(DocumentEntitiesRelationship)
                    .values(rows)
                )
                
                upsert_stmt = stmt.on_conflict_do_update(
                    index_elements=["id"],
                    set_={
                        "description": stmt.excluded.description,
                        "keywords": stmt.excluded.keywords,
                        "strength": stmt.excluded.strength,
                        "confidence": stmt.excluded.confidence,
                        "keys": stmt.excluded['keys'],
                        "value": stmt.excluded.value,
                        "global_themes": stmt.excluded.global_themes,
                        "source_chunks": stmt.excluded.source_chunks,
                        "source_slices": stmt.excluded.source_slices,
                        "occurrence_count": stmt.excluded.occurrence_count,
                        "relationship_vector": stmt.excluded.relationship_vector,
                        "is_bidirectional": stmt.excluded.is_bidirectional,
                        "weight": stmt.excluded.weight,
                        "updated_at": func.now(),
                    },
                ).returning(DocumentEntitiesRelationship)

                self.logger.info("Executing relationship upsert statement...")
                db_models = (await session.execute(upsert_stmt)).scalars().all()
                self.logger.info(f"Relationship upsert executed, got {len(db_models)} results")
                
                await session.commit()
                self.logger.info("Relationship transaction committed successfully")

                self.logger.info(f"create_relationships: returning {len(db_models)} relationships")
                return [model_relationship_db_to_entity(model) for model in db_models]

        except Exception as e:
            self.logger.error(f"Error creating/updating relationships: {str(e)}")
            raise

    async def get_relationships_by_entity_id(self, entity_id: UUID) -> List[EntityRelationship]:
        """Get all relationships for an entity (both source and target)"""
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = select(DocumentEntitiesRelationship).where(
                    or_(
                        DocumentEntitiesRelationship.source_entity_id == entity_id,
                        DocumentEntitiesRelationship.target_entity_id == entity_id
                    )
                )

                result = await session.execute(stmt)
                records = result.scalars().all()
                return [model_relationship_db_to_entity(rel) for rel in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error getting relationships for entity {entity_id}: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error getting relationships for entity {entity_id}: {str(e)}")
            raise

    async def get_relationships_for_entities(self, entity_ids: list[UUID]) -> list[EntityRelationship]:
        if not entity_ids:
            return []
        async with self.sql_db_conn.get_session() as session:
            stmt = (
                select(DocumentEntitiesRelationship)
                .where(
                    or_(
                        DocumentEntitiesRelationship.source_entity_id.in_(entity_ids),
                        DocumentEntitiesRelationship.target_entity_id.in_(entity_ids),
                    )
                )
            )
            res = await session.execute(stmt)
            rows = res.scalars().all()
        return [model_relationship_db_to_entity(r) for r in rows]

    # ==================== Vector Search Methods ====================

    async def vector_search_chunks(self, query_vector: List[float], user_id: str, top_k: int = 10,
                                   similarity_threshold: Optional[float] = None) -> List[DocumentTextChunk]:
        """Search for most similar text chunks using vector similarity."""
        try:
            if not query_vector or not isinstance(query_vector, list):
                raise ValueError("Query vector must be a non-empty list of floats")
            
            # Validate vector dimensions (expecting 1536 for OpenAI embeddings)
            if len(query_vector) != 1536:
                raise ValueError(f"Query vector must have 1536 dimensions, got {len(query_vector)}")
            
            # Validate vector values
            if not all(isinstance(x, (int, float)) for x in query_vector):
                raise ValueError("Query vector must contain only numeric values")

            async with self.sql_db_conn.get_session() as session:
                query = select(DocumentTextChunksModel)

                # Add user_id filter if provided
                if user_id:
                    query = query.where(DocumentTextChunksModel.user_id == user_id)

                # Add similarity threshold filter if provided
                if similarity_threshold is not None:
                    if not (0 <= similarity_threshold <= 1):
                        raise ValueError("Similarity threshold must be between 0 and 1")
                    distance_threshold = 1 - similarity_threshold
                    query = query.where(
                        DocumentTextChunksModel.content_vector.cosine_distance(query_vector) <= distance_threshold
                    )

                query = query.order_by(
                    DocumentTextChunksModel.content_vector.cosine_distance(query_vector)
                ).limit(top_k)

                result = await session.execute(query)
                records = result.scalars().all()

                return [model_text_chunk_db_to_entity(chunk) for chunk in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error performing vector search: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error performing vector search: {str(e)}")
            raise

    async def vector_search_entities(self, query_vector: List[float], user_id: str, top_k: int = 10,
                                     similarity_threshold: Optional[float] = None) -> List[DocumentEntity]:
        """Search for most similar entities using vector similarity."""
        try:
            if not query_vector or not isinstance(query_vector, list):
                raise ValueError("Query vector must be a non-empty list of floats")

            async with self.sql_db_conn.get_session() as session:
                query = select(DocumentEntityModel)

                # Add user_id filter
                if user_id:
                    query = query.where(DocumentEntityModel.user_id == user_id)

                # Add similarity threshold filter if provided
                if similarity_threshold is not None:
                    if not (0 <= similarity_threshold <= 1):
                        raise ValueError("Similarity threshold must be between 0 and 1")
                    distance_threshold = 1 - similarity_threshold
                    query = query.where(
                        DocumentEntityModel.entity_vector.cosine_distance(query_vector) <= distance_threshold
                    )

                query = query.order_by(
                    DocumentEntityModel.entity_vector.cosine_distance(query_vector)
                ).limit(top_k)

                result = await session.execute(query)
                records = result.scalars().all()

                return [model_entity_db_to_entity(entity) for entity in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error performing entity vector search: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error performing entity vector search: {str(e)}")
            raise

    async def vector_search_relationships(self, query_vector: List[float], user_id: str, top_k: int = 10,
                                          similarity_threshold: Optional[float] = None) -> List[EntityRelationship]:
        """Search for most similar relationships using vector similarity."""
        try:
            if not query_vector or not isinstance(query_vector, list):
                raise ValueError("Query vector must be a non-empty list of floats")

            async with self.sql_db_conn.get_session() as session:
                query = select(DocumentEntitiesRelationship)

                # Add user_id filter
                if user_id:
                    query = query.where(DocumentEntitiesRelationship.user_id == user_id)

                # Add similarity threshold filter if provided
                if similarity_threshold is not None:
                    if not (0 <= similarity_threshold <= 1):
                        raise ValueError("Similarity threshold must be between 0 and 1")
                    distance_threshold = 1 - similarity_threshold
                    query = query.where(
                        DocumentEntitiesRelationship.relationship_vector.cosine_distance(
                            query_vector) <= distance_threshold
                    )

                query = query.order_by(
                    DocumentEntitiesRelationship.relationship_vector.cosine_distance(query_vector)
                ).limit(top_k)

                result = await session.execute(query)
                records = result.scalars().all()

                return [model_relationship_db_to_entity(rel) for rel in records]
        except SQLAlchemyError as e:
            self.logger.error(f"Database error performing relationship vector search: {str(e)}")
            raise
        except Exception as e:
            self.logger.error(f"Error performing relationship vector search: {str(e)}")
            raise

    async def rank_chunks_by_vector_and_keywords(self, chunks: List[DocumentTextChunk], query_embedding: List[float],
                                                 high_level_keywords: List[str], low_level_keywords: List[str],
                                                 top_k: int, user_id: str) -> List[DocumentTextChunk]:
        """Rank chunks by combining vector similarity with keyword presence."""
        if not chunks or not query_embedding:
            return chunks[:top_k] if chunks else []

        # Calculate dynamic weighting factors
        query_complexity = len(high_level_keywords) + 0.5 * len(low_level_keywords)
        vector_weight = 1.0
        graph_weight = min(0.5 + (query_complexity * 0.1), 1.0)

        scored_chunks = []

        for chunk in chunks:
            # Calculate keyword score
            keyword_score = 0.0
            if chunk.content:
                chunk_content_lower = chunk.content.lower()
                for keyword in high_level_keywords:
                    if keyword and keyword.lower() in chunk_content_lower:
                        keyword_score += 2.0
                for keyword in low_level_keywords:
                    if keyword and keyword.lower() in chunk_content_lower:
                        keyword_score += 1.0

            # Calculate vector similarity
            vector_similarity = 0.0
            if chunk.content_vector and query_embedding and len(chunk.content_vector) == len(query_embedding):
                vec1 = np.array(chunk.content_vector, dtype=float)
                vec2 = np.array(query_embedding, dtype=float)

                if vec1.ndim == 1 and vec2.ndim == 1:
                    norm1 = np.linalg.norm(vec1)
                    norm2 = np.linalg.norm(vec2)
                    if norm1 > 1e-9 and norm2 > 1e-9:
                        raw_cosine_sim = np.dot(vec1, vec2) / (norm1 * norm2)
                        vector_similarity = (raw_cosine_sim + 1.0) / 2.0

            # Calculate final score
            denominator = vector_weight + graph_weight
            final_score = (vector_similarity * vector_weight + keyword_score * graph_weight) / denominator

            scored_chunks.append((chunk, final_score))

        # Sort and return top_k
        scored_chunks.sort(key=lambda item: item[1], reverse=True)
        return [item[0] for item in scored_chunks[:top_k]]

    async def search_documents_by_prefix(self, user_id: str, prefix: str, limit: int = 10) -> List[UserDocument]:
        """
        Return up to `limit` documents whose file_name starts with `prefix`,
        safely escaping SQL LIKE wildcards.
        """
        if not prefix or not user_id:
            return []

        # escape % and _ so they are treated literally
        esc = prefix.replace('%', r'\\%').replace('_', r'\\_')
        try:
            async with self.sql_db_conn.get_session() as session:
                stmt = (
                    select(UserDocumentsModel)
                    .where(
                        UserDocumentsModel.user_id == user_id,
                        UserDocumentsModel.file_name.ilike(f"{esc}%")
                    )
                    .limit(limit)
                )
                result = await session.execute(stmt)
                rows = result.scalars().all()
                return [model_document_db_to_entity(r) for r in rows]
        except SQLAlchemyError as e:
            self.logger.error("DB error in search_documents_by_prefix")
            raise e
        except Exception as e:
            self.logger.error("Unexpected error in search_documents_by_prefix")
            raise e

    async def search_relevant_documents_word_based(self, user_id: str, query: str, limit: int = 30) -> List[
        UserDocument]:

        # Check if the query is just whitespace
        if not query or not query.strip():
            self.logger.info(f"Whitespace query detected for user_id={user_id}, fetching latest 20 documents.")
            try:
                async with self.sql_db_conn.get_session() as session:
                    stmt = (
                        select(UserDocumentsModel)
                        .where(UserDocumentsModel.user_id == user_id)
                        .order_by(UserDocumentsModel.created_at.desc())
                        .limit(limit)  # Limit to 20 as requested
                    )
                    result = await session.execute(stmt)
                    documents = result.scalars().all()

                    return [model_document_db_to_entity(r) for r in documents]
            except SQLAlchemyError as e:
                self.logger.error(f"DB error fetching latest documents for whitespace query: {e}")
                raise
            except Exception as e:
                self.logger.error(f"Unexpected error fetching latest documents for whitespace query: {e}")
                raise

        # Proceed with the original full-text search logic if query is not whitespace
        self.logger.info(f"search_relevant_documents_word_based: user_id={user_id}, query='{query}', limit={limit}")

        try:
            async with self.sql_db_conn.get_session() as session:
                sql = text("""
                           WITH combined AS (SELECT *, 0 AS rank_priority, NULL::float8 AS rank_score
                                             FROM user_documents
                                             WHERE user_id = :user_id
                                               AND LOWER(file_name) = LOWER(:q)

                                             UNION ALL

                                             SELECT *,
                                                    CASE
                                                        WHEN LOWER(file_name) LIKE '%' || LOWER(:q) || '%' THEN 1
                                                        ELSE 2 END                          AS rank_priority,
                                                    ts_rank(to_tsvector('english', COALESCE(content, '')),
                                                            plainto_tsquery('english', :q)) AS rank_score
                                             FROM user_documents
                                             WHERE user_id = :user_id
                                               AND LOWER(file_name)
                               != LOWER (:q)
                               AND to_tsvector('english'
                              , COALESCE (content
                              , '')) @@ plainto_tsquery('english'
                              , :q)
                               )

                           SELECT *
                           FROM combined
                           ORDER BY rank_priority ASC, rank_score DESC LIMIT :limit

                           """)

                rows = await session.execute(
                    sql,
                    {'user_id': user_id, 'q': query, 'limit': limit}
                )
                records = rows.fetchall()

                return [model_document_db_to_entity(r) for r in records]

        except SQLAlchemyError as e:
            self.logger.error(f"DB error in search_relevant_documents_word_based: {e}")
            raise
        except Exception as e:
            self.logger.error(f"Unexpected error in search_relevant_documents_word_based: {e}")
            raise