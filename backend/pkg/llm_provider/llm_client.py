from collections.abc import AsyncGenerator
from enum import Enum
from typing import Any, List, Dict, Optional, Tuple, Union

from openai import AsyncOpenAI
from openai.types.shared_params.response_format_json_object import ResponseFormatJSONObject
from pkg.llm_provider.claude_aws.claude_client import BedrockAnthropicClient
from pkg.log.logger import Logger
from google import genai
from app.tokens.service.service import TokensService
import tiktoken


class LLMModel(Enum):
    DEEPSEEK_V3: str = "DEEPSEEK_V3"
    GPT_4O: str = "GPT_4O"
    GPT_4O_MINI: str = "GPT_4O_MINI"
    GPT_4_1_MINI: str = "GPT_4_1_MINI"
    GPT_4_1: str = "GPT_4_1"
    O1_PREVIEW: str = "O1_PREVIEW"
    O1_MINI: str = "O1_MINI"
    CLAUDE_3_SONNET: str = "CLAUDE_3.5_SONNET"
    LLAMA_3_5_70B: str = "LLAMA_3.5-70B"
    LLAMA_3_2_11B: str = "LLAMA_3.2-11B"
    LLAMA_3_2_90B: str = "LLAMA_3.2-90B"
    LLAMA_4_MAVERICK: str = "LLAMA_4_MAVERICK"
    LLAMA_4_SCOUT: str = "LLAMA_4_SCOUT"

    DEEPSEEK_R1: str = "DEEPSEEK_R1"
    GEMINI_2_0_FLASH: str = "GEMINI_2_0_FLASH"
    GEMINI_2_0_FLASH_LITE: str = "GEMINI_2_0_FLASH_LITE"
    GEMINI_2_5_PRO_EXP: str = "GEMINI_2_5_PRO_EXP"
    GEMINI_2_5_FLASH: str = "GEMINI_2_5_FLASH"

    CLAUDE_3_7_SONNET: str = "CLAUDE_3_7_SONNET"


deepseek_model_map = {
    "DEEPSEEK_V3": "deepseek-chat",
}

openai_model_map = {
    "O3": "o3",
    "O3_MINI": "o3-mini",
    "O4_MINI": "o4-mini",
    "GPT_4O": "gpt-4o-latest",
    "GPT_4O_MINI": "gpt-4o-mini",
    "GPT_4_1_MINI": "gpt-4.1-mini",
    "GPT_4_1": "gpt-4.1",
    "GPT_4_1_NANO": "gpt-4.1-nano",

}

groq_model_map = {
    "LLAMA_3.5-70B": "llama-3.3-70b-versatile",
    "LLAMA_3.2-11B": "llama-3.2-11b-vision-preview",
    "LLAMA_3.2-90B": "llama-3.2-90b-vision-preview",
    "DEEPSEEK_R1": "deepseek-r1-distill-llama-70b",
    "LLAMA_4_MAVERICK": "meta-llama/llama-4-maverick-17b-128e-instruct",
    "LLAMA_4_SCOUT": "meta-llama/llama-4-scout-17b-16e-instruct"

}

gemini_model_map = {
    "GEMINI_2_0_FLASH": "gemini-2.0-flash",
    "GEMINI_2_0_FLASH_LITE": "gemini-2.0-flash-lite",
    "GEMINI_2_5_PRO_EXP": "gemini-2.5-pro-preview-05-06",
    "GEMINI_2_5_FLASH":"gemini-2.5-flash-preview-05-20"
}

bedrock_anthropic_model_map = {
    "CLAUDE_3_7_SONNET": "eu.anthropic.claude-3-7-sonnet-20250219-v1:0",
}


class EmbeddingModel(Enum):
    TEXT_EMBEDDING_3_SMALL = "text-embedding-3-small"


class LLMClient:
    def __init__(self, openai_api_key: str, groq_api_key: str, google_api_key: str,
                 logger: Logger, tokens_service: TokensService,
                 bedrock_anthropic_client: Optional[BedrockAnthropicClient] = None):
        self.open_ai_client: AsyncOpenAI = AsyncOpenAI(api_key=openai_api_key)
        self.google_api_key: str = google_api_key
        if self.google_api_key:  # Initialize Gemini client only if the key is provided
            self.gemini_client: AsyncOpenAI = AsyncOpenAI(
                api_key=google_api_key,
                base_url="https://generativelanguage.googleapis.com/v1beta/openai/"
            )
        self.groq_client: AsyncOpenAI = AsyncOpenAI(api_key=groq_api_key, base_url="https://api.groq.com/openai/v1")
        self.logger: Logger = logger
        self.tokens_service: TokensService = tokens_service
        if bedrock_anthropic_client:
            self.claude_client: BedrockAnthropicClient = bedrock_anthropic_client()

    def num_tokens_from_string(self, string: str, model: str = "cl100k_base") -> int:

        try:
            encoding = tiktoken.get_encoding(model)
            num_tokens: int = len(encoding.encode(string))
            return num_tokens
        except Exception as e:
            self.logger.error(f"Error calculating tokens with tiktoken: {e}. Falling back to character estimate.")
            # Fallback to character-based estimation (4 chars ≈ 1 token)
            return len(string) // 4

    def estimate_tokens(self, messages: List[Dict[str, Any]]) -> int:

        # Choose encoding based on model family
        encoding_name: str = "cl100k_base"  # Default for most models

        # Combine all message content for token counting
        combined_token_count = 0
        for message in messages:
            if isinstance(message.get("content"), str):
                combined_token_count += self.num_tokens_from_string(message["content"], encoding_name)

        return combined_token_count

    async def get_completion(self, model: str, prompt: str, temperature: float = 0.1, seed: int = None,
                             user_id: Optional[str] = None) -> str:
        self.logger.info(f"LLMClient.get_completion - Called with model: {model}")

        # Convert string model name to enum if needed
        model_enum = None
        for llm_model in LLMModel:
            if (llm_model.value == model.upper() or model.lower() in openai_model_map.get(llm_model.value,
                                                                                          "").lower() or
                    model.lower() in gemini_model_map.get(llm_model.value, "").lower()):
                model_enum = llm_model
                break

        # If we couldn't map it, default to GPT-4o-mini
        if not model_enum:
            self.logger.warning(f"LLMClient.get_completion -Couldn't map model name:{model}, defaulting to GPT_4O_MINI")
            model_enum = LLMModel.GEMINI_2_0_FLASH

        # Check token availability if user_id is provided
        if user_id:
            input_tokens = self.num_tokens_from_string(prompt)
            token_check = await self.tokens_service.check_token_limit(user_id, input_tokens)
            if not token_check:
                return "Insufficient tokens to complete this request. Please upgrade your plan."

        # Call the actual implementation
        response: str = await self.get_response(
            prompt=prompt,
            model=model_enum,
            system_msg="",  # No system message in get_completion interface
            temperature=temperature,
            user_id=user_id
        )

        return response

    async def get_response(self, prompt: str, model: LLMModel, system_msg: str = "",
                           temperature: float = 0.3, max_tokens: int = 8000, user_id: Optional[str] = None,
                           response_format: Optional[dict] =None) -> str:
        # Prepare messages
        if response_format is None:
            response_format = {"type": "text"}
        messages: list[dict] = [
            {"role": "system", "content": system_msg},
            {"role": "user", "content": prompt},
        ]

        # Check token availability if user_id is provided
        if user_id:
            token_check: bool = await self.tokens_service.check_token_limit(user_id, 1)
            if not token_check:
                return "Insufficient tokens to complete this request. Please upgrade your plan."

        try:

            if model in (LLMModel.LLAMA_3_5_70B, LLMModel.DEEPSEEK_R1, LLMModel.LLAMA_3_2_90B,
                         LLMModel.LLAMA_4_SCOUT, LLMModel.LLAMA_4_MAVERICK):
                response = await self.groq_client.chat.completions.create(
                    model=groq_model_map[model.value],
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,

                )
                response_text = response.choices[0].message.content

                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                return response_text

            elif model in (LLMModel.GEMINI_2_0_FLASH, LLMModel.GEMINI_2_0_FLASH_LITE, LLMModel.GEMINI_2_5_PRO_EXP, LLMModel.GEMINI_2_5_FLASH):
                try:
                    model_value = gemini_model_map.get(model.value)
                    response = await self.gemini_client.chat.completions.create(
                        model=model_value,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format = response_format,

                    )
                    response_text = response.choices[0].message.content

                    # Update token consumption if user_id is provided
                    if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                        await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                    return response_text

                except Exception as e:
                    self.logger.error(f"Error getting response from Gemini: {e!s}")
                    raise e
            elif model == LLMModel.CLAUDE_3_7_SONNET:
                response = await self.claude_client.messages.create(
                    model=bedrock_anthropic_model_map.get(model.value),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                response_text = response.content[0].text

                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage'):
                    total_tokens = response.usage.input_tokens + response.usage.output_tokens
                    await self.tokens_service.consume_tokens(user_id, total_tokens)

                return response_text
            else:
                # model should be mapped and extracted from openai model
                model_value = openai_model_map.get(model.value)
                response = await self.open_ai_client.chat.completions.create(
                    model=model_value,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                response_text = response.choices[0].message.content

                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                return response_text

        except Exception as e:
            # If an error occurs, refund the pre-consumed tokens
            self.logger.error(f"Error in get_response: {e}")
            raise e

    async def get_response_stream(self, messages: list[dict], model: LLMModel, temperature: float = 0.3,
            user_id: Optional[str] = None, system_message="") -> AsyncGenerator[Any, None]:

        # Check token availability if user_id is provided
        if user_id:
            token_check: int = await self.tokens_service.check_token_limit(user_id, 10)
            if not token_check:
                self.logger.error("Insufficient tokens to complete this request. Please upgrade your plan.")
                return
        token_count = 0
        system_msg_dict = {
            "role": "system",
            "content": system_message,
        }
        try:

            if model in (LLMModel.LLAMA_3_5_70B, LLMModel.DEEPSEEK_R1):
                messages.insert(0, system_msg_dict)
                stream = await self.groq_client.chat.completions.create(
                    model=groq_model_map.get(model.value),
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                    stream_options={"include_usage": True},
                )
                async for chunk in stream:
                    # Extract the text content from the ChatCompletionChunk
                    if hasattr(chunk, "choices") and chunk.choices:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                    if hasattr(chunk, "usage") and hasattr(chunk.usage, "total_tokens"):
                        token_count += chunk.usage.total_tokens
            elif model in (LLMModel.GEMINI_2_0_FLASH, LLMModel.GEMINI_2_0_FLASH_LITE, LLMModel.GEMINI_2_5_PRO_EXP, LLMModel.GEMINI_2_5_FLASH):
                messages.insert(0, system_msg_dict)
                print("messages", messages)
                model_value = gemini_model_map.get(model.value)
                stream = await self.gemini_client.chat.completions.create(
                    model=model_value,
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                    stream_options={"include_usage": True},
                )
                async for chunk in stream:
                    # Extract the text content from the ChatCompletionChunk
                    if hasattr(chunk, "choices") and chunk.choices:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                    if hasattr(chunk, "usage") and hasattr(chunk.usage, "total_tokens"):
                        token_count += chunk.usage.total_tokens
            elif model == LLMModel.CLAUDE_3_7_SONNET:
                async with await self.claude_client.messages.create(
                        max_tokens=64000,
                        model=bedrock_anthropic_model_map.get(model.value),
                        messages=messages,
                        temperature=temperature,
                        stream=True,
                        system=system_message,
                ) as stream:
                    async for event in stream:
                        if event.type == "content_block_delta":
                            content = event.delta.text
                            if content:
                                yield content
                        elif event.type == "message_start":
                            token_count += event.message.usage.input_tokens
                        elif event.type == "message_delta":
                            token_count += event.usage.output_tokens

            else:
                messages.insert(0, system_msg_dict)
                # model should be mapped and extracted from openai model
                model_value = openai_model_map.get(model.value)
                stream = await self.open_ai_client.chat.completions.create(
                    model=model_value,
                    messages=messages,
                    temperature=temperature,
                    stream=True,
                    stream_options={"include_usage": True},
                )
                async for chunk in stream:
                    # Extract the text content from the ChatCompletionChunk
                    if hasattr(chunk, "choices") and chunk.choices:
                        content = chunk.choices[0].delta.content
                        if content:
                            yield content
                    if hasattr(chunk, "usage") and hasattr(chunk.usage, "total_tokens"):
                        token_count += chunk.usage.total_tokens
            # Update token consumption if user_id is provided
            if user_id and token_count > 0:
                await self.tokens_service.consume_tokens(user_id, token_count)


        except Exception as e:
            self.logger.error(f"Error in get_response_stream: {e}")
            raise e

    async def create_embeddings(self, texts: list[str], model: EmbeddingModel) -> list[list[float]]:
        response = await self.open_ai_client.embeddings.create(
            input=texts, model=model.value
        )
        return [embedding.embedding for embedding in response.data]

    async def get_embedding(self, text: str, model: EmbeddingModel = EmbeddingModel.TEXT_EMBEDDING_3_SMALL) -> list[
        float]:

        embeddings = await self.create_embeddings([text], model)
        return embeddings[0] if embeddings else []

    async def get_response_of_message_list(self, messages: list[dict], model: LLMModel, temperature: float = 0.1,
                                           max_tokens: int = 8000, user_id: Optional[str] = None, response_format: Optional[Any] =None) -> Any:
        # Check token availability if user_id is provided
        if user_id:
            token_check: int = await self.tokens_service.check_token_limit(user_id, 10)
            if not token_check:
                self.logger.error("Insufficient tokens to complete this request. Please upgrade your plan.")
                return

        try:

            if model in (LLMModel.LLAMA_3_5_70B, LLMModel.DEEPSEEK_R1):
                response = await self.groq_client.chat.completions.create(
                    model=groq_model_map.get(model.value),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                response_text = response.choices[0].message.content


                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                return response_text

            elif model in (LLMModel.GEMINI_2_0_FLASH, LLMModel.GEMINI_2_0_FLASH_LITE, LLMModel.GEMINI_2_5_PRO_EXP, LLMModel.GEMINI_2_5_FLASH):
                try:

                    model_value = gemini_model_map.get(model.value)
                    print("messages", messages, "model", model_value, "response_format", response_format)
                    response = await self.gemini_client.chat.completions.create(
                        model=model_value,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                        response_format = response_format,

                    )
                    response_text = response.choices[0].message.content

                    # Update token consumption if user_id is provided
                    if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                        await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                    return response_text

                except Exception as e:
                    self.logger.error(f"Error getting response from Gemini: {e!s}")
                    raise e
            elif model == LLMModel.CLAUDE_3_7_SONNET:
                response = await self.claude_client.messages.create(
                    model=bedrock_anthropic_model_map.get(model.value),
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                )
                response_text = response.content[0].text

                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage'):
                    total_tokens = response.usage.input_tokens + response.usage.output_tokens
                    await self.tokens_service.consume_tokens(user_id, total_tokens)

                return response_text
            else:
                # model should be mapped and extracted from openai model
                model_value = openai_model_map.get(model.value)
                if response_format is None:
                    response = await self.open_ai_client.chat.completions.create(
                        model=model_value,
                        messages=messages,
                        temperature=temperature,
                        max_tokens=max_tokens,
                    )
                    response_text = response.choices[0].message.content
                    if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                        await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                    return response_text

                response = await self.open_ai_client.beta.chat.completions.parse(
                    model=model_value,
                    messages=messages,
                    temperature=temperature,
                    max_tokens=max_tokens,
                    response_format=response_format,
                )
                response_text = response.choices[0].message.parsed

                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                return response_text

        except Exception as e:
            # If an error occurs, refund the pre-consumed tokens
            self.logger.error(f"Error in get_response: {e}")
            raise e

    async def get_image_description(self, base64_image: str, model: LLMModel,
                                    prompt: str = "What is in this image?", user_id: Optional[str] = None) -> str:
        """Get description of an image"""

        # Check token availability if user_id is provided
        pre_consumed = 0
        if user_id:
            token_check = await self.tokens_service.check_token_limit(user_id, 1)
            if not token_check:
                return "Insufficient tokens to complete this request. Please upgrade your plan."

        try:
            if model == LLMModel.DEEPSEEK_V3:
                raise Exception("Deepseek does not support image description")
            elif model in (LLMModel.LLAMA_3_5_70B, LLMModel.LLAMA_3_2_11B, LLMModel.LLAMA_3_2_90B):
                response = await self.groq_client.chat.completions.create(
                    model=groq_model_map.get(model.value),
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                )
                response_text = response.choices[0].message.content

                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                return response_text

            elif model in (LLMModel.GEMINI_2_0_FLASH, LLMModel.GEMINI_2_0_FLASH_LITE, LLMModel.GEMINI_2_5_PRO_EXP):
                model_value = gemini_model_map[model.value]
                response = await self.gemini_client.chat.completions.create(
                    model=model_value,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                )
                response_text = response.choices[0].message.content
                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                return response_text

            elif model == LLMModel.CLAUDE_3_7_SONNET:
                model_value = bedrock_anthropic_model_map.get(model.value)
                response = await self.claude_client.messages.create(
                    model=model_value,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                                {
                                    "type": "image",
                                    "source": {
                                        "type": "base64",
                                        "media_type": "image/png",
                                        "data": base64_image,
                                    },
                                },
                            ],
                        }
                    ],
                )
                response_text = response.content[0].text
                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage'):
                    total_tokens = response.usage.input_tokens + response.usage.output_tokens
                    await self.tokens_service.consume_tokens(user_id, total_tokens)
                return response_text

            else:
                model_value = openai_model_map.get(model.value)
                response = await self.open_ai_client.chat.completions.create(
                    model=model_value,
                    messages=[
                        {
                            "role": "user",
                            "content": [
                                {
                                    "type": "text",
                                    "text": prompt,
                                },
                                {
                                    "type": "image_url",
                                    "image_url": {
                                        "url": f"data:image/jpeg;base64,{base64_image}"
                                    },
                                },
                            ],
                        }
                    ],
                )
                response_text = response.choices[0].message.content

                # Update token consumption if user_id is provided
                if user_id and hasattr(response, 'usage') and hasattr(response.usage, 'total_tokens'):
                    await self.tokens_service.consume_tokens(user_id, response.usage.total_tokens)

                return response_text

        except Exception as e:
            # If an error occurs, refund the pre-consumed tokens
            if user_id and pre_consumed > 0:
                await self.tokens_service.refill_tokens(
                    user_id=user_id,
                    amount=pre_consumed,
                    description="Refund for failed image description request"
                )
            raise e
