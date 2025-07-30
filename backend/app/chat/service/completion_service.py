from app.pal.chat.agent import ChatAgent  # Updated import for our new ChatAgent
from app.pal.analytics.analytics_workflow import AnalyticsPAL
from app.pal.knowledge_pal.agent import KnowledgePalAgent
from app.chat.service.chat_service import ChatService
from pkg.log.logger import Logger

from app.chat.entity.chat import Conversation, Message, Document, CompletionRequest, Suggestion, SuggestionContent, \
    Artifact, KnowledgeResponse, Reference
from typing import AsyncGenerator, Dict, Any, Union, List
from uuid import UUID
import asyncio
import json


class ChatCompletionService:
    def __init__(self, chat_service: ChatService, chat_agent: ChatAgent, analytics_pal: AnalyticsPAL, logger: Logger,
                 knowledge_pal: KnowledgePalAgent):
        self.chat_service: ChatService = chat_service
        self.chat_agent: ChatAgent = chat_agent
        self.knowledge_pal: KnowledgePalAgent = knowledge_pal
        self.analytics_pal: AnalyticsPAL = analytics_pal
        self.logger: Logger = logger
        self._external_call_timeout = 360  # seconds

    async def create_completion(self, user_id: str, conversation_id: UUID, completion_request: CompletionRequest
                                ) -> AsyncGenerator[Union[str, Dict[str, Any]], None]:
        chunks = []
        stop_reason = "end_turn"
        suggestions = []
        artifacts = []
        references = []
        meta_contents = []
        conversation = None
        user_message = None  # Define user_message here to access in finally

        try:
            conversation: Conversation = await self.chat_service.get_conversation(user_id, conversation_id)



            if not conversation:
                self.logger.error(f"Conversation not found for user {user_id}, conversation {conversation_id}")
                raise ValueError("Conversation not found")
            if conversation.model != completion_request.model:
                self.logger.info(f"Updating conversation model from {conversation.model} to {completion_request.model}")
                # Update the conversation model if it has changed
                conversation.model = completion_request.model
                await self.chat_service.update_conversation_model(user_id,conversation_id,completion_request.model)


            # Update conversation title more efficiently (only for first few messages)
            if len(conversation.messages) < 3:
                await self.chat_service.update_conversation_title(conversation, user_id, conversation_id)

            # Create and store user message
            user_message = await self.chat_service.create_user_message(conversation_id, completion_request,
                                                                       conversation.model)
            await self.chat_service.add_message(user_id, conversation_id, user_message)

            # Process based on model type with timeout protection
            if conversation.model == "ANALYST_PAL":
                # Analyst PAL processing
                async for item in self._process_analyst_pal(user_id, completion_request, conversation_id, chunks,
                                                            suggestions, artifacts, meta_contents):
                    yield item
            else:
                if conversation.model == "KNOWLEDGE_PAL":
                    # Knowledge PAL processing using new streaming method
                    # Format the conversation history into a list of messages
                    conversation_history = conversation.messages if hasattr(conversation, 'messages') else []
                    
                    async for item in self.knowledge_pal.stream_knowledge_response(
                            user_id=user_id,
                            request=completion_request,
                            conversation_history=conversation_history
                    ):
                        if isinstance(item, str):
                            # Handle plain string responses for backward compatibility
                            chunks.append(item)
                            yield item
                        elif isinstance(item, Reference):
                            references.append(item)
                            self.logger.info(f"Received document references from KnowledgePAL")
                            yield {"type": "references", "references": item}
                        elif isinstance(item, dict):
                            # Handle legacy dictionary format for backward compatibility
                            if item.get("type") == "references":
                                # Process references from knowledge PAL
                                if "references" in item and item["references"]:
                                    references.extend(item["references"])
                                    self.logger.info(f"Received {len(item['references'])} document references from KnowledgePAL")
                                # Forward references to client
                                async for ref_item in self._handle_references_response(item, references):
                                    yield ref_item
                            elif item.get("type") == "meta_content":
                                meta_contents.append(item["meta_content"])
                                async for value in self._handle_meta_content_response(item):
                                    yield value
                            else:
                                content = item.get("content", "")
                                if content:
                                    chunks.append(content)
                                    yield content
                else:
                    # For all other model types including None, use ChatAgent
                    async with asyncio.timeout(self._external_call_timeout):
                        # Process the completion using the ChatAgent
                        # First format the conversation history into a list of messages
                        conversation_history = conversation.messages if hasattr(conversation, 'messages') else []

                        async for response in self.chat_agent.stream_completion_request(
                            user_id=user_id,
                            request=completion_request,
                            conversation_history=conversation_history
                        ):
                            if isinstance(response, str):
                                # Handle string responses
                                chunks.append(response)
                                yield response
                            # Handle suggestions
                            elif isinstance(response, dict) and response.get("type") == "suggestions":
                                async for item in self._handle_suggestions_response(response, suggestions):
                                    yield item
                            # Handle artifacts
                            elif isinstance(response, dict) and response.get("type") == "artifacts":
                                async for item in self._handle_artifacts_response(response, artifacts):
                                    yield item
                            # Handle meta content
                            elif isinstance(response, dict) and response.get("type") == "meta_content":
                                # Store the meta_content for later use when saving the message
                                if "meta_content" in response and response["meta_content"]:
                                    meta_contents.append(response["meta_content"])
                                async for item in self._handle_meta_content_response(response):
                                    yield item
                            # Handle data summary delta
                            elif isinstance(response, dict) and response.get("type") == "data_summary_delta":
                                async for item in self._handle_data_summary_delta_response(response):
                                    yield item
                            elif isinstance(response, dict) and response.get("type") == "references":
                                # Store the references for later use when saving the message
                                if "references" in response and response["references"]:
                                    references.extend(response["references"])
                                async for item in self._handle_references_response(response, references):
                                    yield item
                            elif isinstance(response, dict):
                                # Handle other dictionary responses
                                content = response.get("content", response.get("response", ""))
                                if content:
                                    chunks.append(content)
                                    yield content
                            else:
                                # Handle unexpected response types
                                self.logger.error(f"Unexpected response type: {type(response)}")
                                error_msg = f"Unexpected response type: {type(response)}"
                                chunks.append(error_msg)
                                yield error_msg


        except asyncio.CancelledError:
            self.logger.warning(f"Completion request cancelled for user {user_id}, conversation {conversation_id}")
            stop_reason = "user_canceled"
            raise
        except asyncio.TimeoutError:
            error_msg = f"Processing timed out after {self._external_call_timeout} seconds"
            self.logger.error(error_msg)
            chunks.append(error_msg)
            yield error_msg
            stop_reason = "timeout"
        except Exception as e:
            self.logger.error(
                f"Error in create_completion for user {user_id}, conversation {conversation_id}: {str(e)}",
                exc_info=True)
            error_msg = f"An error occurred: {str(e)}"
            chunks.append(error_msg)
            yield error_msg
            stop_reason = "error"
        finally:
            # Store the assistant message if user_message was created
            if user_message:
                final_metadata_to_store = meta_contents

                await self.chat_service.store_assistant_message(
                    user_id, conversation_id,
                    chunks,
                    stop_reason,
                    user_message.id,  # Parent is the user message that triggered this turn
                    conversation.model,
                    suggestions, artifacts,
                    references=references,
                    meta_contents=final_metadata_to_store
                )

    async def _process_analyst_pal(self, user_id: str, completion_request, conversation_id: UUID, chunks, suggestions,
                                   artifacts, meta_contents):
        """Process ANALYST_PAL model interactions with better error handling"""
        self.logger.info(
            f"Processing with ANALYST_PAL - Database UID: '{completion_request.database_uid}', "
            f"Table UID: '{completion_request.table_uid}'"
        )

        # Prepare suggestions
        suggestions_dict = [
            {
                "type": suggestion.__dict__["type"],
                "suggestion_content": suggestion.suggestion_content.__dict__,
            }
            for suggestion in completion_request.selected_suggestions
        ]

        # Process analytics with timeout protection
        async with asyncio.timeout(self._external_call_timeout):
            async for response in self.analytics_pal.handle_message(
                    user_id,
                    completion_request.prompt,
                    conversation_id,
                    [attachment.__dict__ for attachment in completion_request.attachments],
                    conversation_id,
                    suggestions_dict,
                    completion_request.database_uid,
                    completion_request.table_uid,
            ):
                # Handle suggestions
                if isinstance(response, dict) and response.get("type") == "suggestions":
                    async for item in self._handle_suggestions_response(response, suggestions):
                        yield item
                # Handle artifacts
                elif isinstance(response, dict) and response.get("type") == "artifacts":
                    async for item in self._handle_artifacts_response(response, artifacts):
                        yield item
                # Handle meta content
                elif isinstance(response, dict) and response.get("type") == "meta_content":
                    # Store the meta_content for later use when saving the message
                    if "meta_content" in response and response["meta_content"]:
                        meta_contents.append(response["meta_content"])
                    async for item in self._handle_meta_content_response(response):
                        yield item
                # Handle data summary delta
                elif isinstance(response, dict) and response.get("type") == "data_summary_delta":
                    async for item in self._handle_data_summary_delta_response(response):
                        yield item
                # Handle content
                else:
                    content = response.get("content", response.get("response", ""))
                    if content:
                        chunks.append(content)
                        yield {"content": content}

    async def _handle_suggestions_response(self, response, suggestions):
        """Helper to process suggestion responses"""
        suggestions_resp = response.get("suggestions", [])
        suggestion_list = []

        for suggestion in suggestions_resp:
            # Check if suggestion is already a Suggestion object
            if isinstance(suggestion, Suggestion):
                suggestion_list.append(suggestion)
            else:
                # Handle dictionary format
                suggestion_list.append(
                    Suggestion(
                        type=suggestion["type"],
                        suggestion_content=SuggestionContent(
                            text=suggestion["suggestion_content"]["text"]
                        ),
                    )
                )

        suggestions.extend(suggestion_list)
        yield {"type": "suggestions", "suggestions": suggestion_list}

    async def _handle_artifacts_response(self, response, artifacts):
        """Helper to process artifact responses with better logging and error handling"""
        self.logger.info("Processing artifacts response")
        artifacts_resp = response.get("artifacts", [])
        artifact_list = []

        for artifact in artifacts_resp:
            try:
                # Check if artifact is already an Artifact object
                if isinstance(artifact, Artifact):
                    artifact_list.append(artifact)
                else:
                    # Handle dictionary format
                    artifact_list.append(
                        Artifact(
                            artifact_type=artifact["artifact_type"],
                            content=artifact["content"]
                        )
                    )
            except Exception as e:
                self.logger.error(f"Error creating artifact: {str(e)}")

        # Extend main artifacts list
        artifacts.extend(artifact_list)
        # Yield to client
        yield {"type": "artifacts", "artifacts": artifact_list}


    async def _handle_meta_content_response(self, response):
        """Helper to process meta content responses"""
        if isinstance(response, dict) and response.get("type") == "meta_content":
            # Just yield the meta_content without affecting the message content
            yield {"type": "meta_content", "meta_content": response["meta_content"]}

    async def _handle_data_summary_delta_response(self, response):
        """Helper to process data summary delta responses"""
        if isinstance(response, dict) and response.get("type") == "data_summary_delta":
            yield {"type": "data_summary_delta", "data_summary_delta": response["content"]}

    async def _handle_references_response(self, response, references):
        """Helper to process references responses"""
        if isinstance(response, dict) and response.get("type") == "references":
            references = response.get("references", [])
            yield {"type": "references", "references": references}