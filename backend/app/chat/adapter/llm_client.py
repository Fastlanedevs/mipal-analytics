from collections.abc import AsyncGenerator

from app.chat.service.chat_service import ILLMAdapter
from pkg.llm_provider.llm_client import LLMClient, LLMModel, EmbeddingModel
from pkg.log.logger import Logger


class LLMAdapter(ILLMAdapter):
    def __init__(self, llm_client: LLMClient, logger: Logger):
        self.client = llm_client
        self.logger = logger

    async def get_completion_stream( self,user_id:str, messages: list[dict], model: str, temperature: float = 0.1
    ) -> AsyncGenerator[str, None]:
        chat_model = LLMModel(model)
        stream = await self.client.get_response_stream(
            messages, chat_model, temperature, user_id
        )
        async for chunk in stream:
                yield chunk

    async def get_image_description(
            self, base64_image: str, prompt: str = "What is in this image?"
    ) -> str:
        try:
            description = await self.client.get_image_description(
                base64_image=base64_image, model=LLMModel.GEMINI_2_0_FLASH
            )
            return description
        except Exception as e:
            self.logger.error(f"Error getting image description: {e!s}")
            raise

    async def get_completion(self, query: str, system_msg: str = "Give a short title for the conversation",
                             temperature: float = 1,) -> str:
        try:
            completion = await self.client.get_response(
                query, LLMModel.GEMINI_2_0_FLASH_LITE, system_msg, temperature
            )
            return completion
        except Exception as e:
            self.logger.error(f"Error getting completion: {e!s}")
            raise

    async def create_embedding(self, query: str) -> list[float]:
        try:
            embeddings = await self.client.create_embeddings([query], EmbeddingModel.TEXT_EMBEDDING_3_SMALL)
            return embeddings[0]
        except Exception as e:
            self.logger.error(f"Error creating embedding: {e!s}")
            raise e
