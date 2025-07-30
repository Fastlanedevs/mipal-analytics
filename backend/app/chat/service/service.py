from abc import ABC, abstractmethod
from typing import Optional, List, Tuple, AsyncGenerator, Dict, Any
from app.chat.entity.chat import Conversation, Message
from uuid import UUID


class IChatRepository(ABC):
    @abstractmethod
    async def save_conversation(self, user_id: str, conversation: Conversation) -> str:
        pass

    @abstractmethod
    async def save_message(self, user_id: str, message: Message) -> str:
        pass

    @abstractmethod
    async def get_conversation(self, user_id: str, conversation_id: UUID, include_messages: bool = True,
                               page: int = 1, page_size: int = 100000) -> Optional[Conversation]:
        pass

    @abstractmethod
    async def list_conversations(self, user_id: str, pal: str = None) -> List[Conversation]:
        pass

    @abstractmethod
    async def delete_conversation(self, conversation_id: UUID, user_id: str):
        pass

    @abstractmethod
    async def update_conversation_model(self, user_id: str, conversation_id: UUID,
                                        conversation_model: str) -> Conversation:
        pass

    @abstractmethod
    async def get_message(self,user_id: str, message_id: UUID) -> Message:
        pass

    @abstractmethod
    async def update_conversation_name(self, user_id: str, conversation_id: UUID, name: str):
        pass


class ILLMAdapter(ABC):
    @abstractmethod
    async def get_completion_stream(self, user_id: str, messages: list[dict], model: str,
                                    temperature: float = 0.1) -> AsyncGenerator[str, None]:
        pass

    @abstractmethod
    async def get_image_description(self, base64_image: str, prompt: str = "What is in this image?") -> str:
        pass

    @abstractmethod
    async def get_completion(self, query: str, system_msg: str = "Give a short title for the conversation",
                             temperature: float = 1) -> str:
        pass

    @abstractmethod
    async def create_embedding(self, query: str) -> List[float]:
        pass
