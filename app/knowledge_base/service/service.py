import uuid
from uuid import UUID
import hashlib
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Dict, List, Any, Optional, Tuple, Union
from app.knowledge_base.entity.entity import (
    UserDocument, SyncIntegration, UserIntegration
)
from pkg.util.file_content_extractor import ExtractedContent






class IKnowledgeBaseRepository(ABC):
    """Interface for Knowledge Base Repository with LightRAG Mix technique support"""

    # Document Management





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




class IKnowledgeIngestionService(ABC):
    """Interface for knowledge ingestion services"""

    @abstractmethod
    async def sync_integration(self, user_id: str, sync_id: UUID) -> dict[str, int]:
        pass

