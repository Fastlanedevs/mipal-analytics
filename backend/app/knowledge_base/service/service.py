import uuid
from uuid import UUID
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, Tuple, Union
from app.knowledge_base.entity.entity import UserIntegration, SyncIntegration



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




class IKnowledgeIngestionService(ABC):
    """Interface for knowledge ingestion services"""

    @abstractmethod
    async def sync_integration(self, user_id: str, sync_id: UUID) -> dict[str, int]:
        pass


