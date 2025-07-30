# handlers.py
import asyncio
from collections.abc import AsyncIterator
from typing import Any
from uuid import uuid4, UUID

from fastapi import HTTPException
from fastapi.responses import StreamingResponse

from app.chat.api.dto import (
    PAL,
    Artifact,
    Reference,
    CompletionRequest,
    ConversationDTO,
    CreateConversationRequest,
    CreateConversationResponse,
    FileExtractRequest,
    FileExtractResponse,
    GetConversationResponse,
    ListConversationsResponse,
    MessageDTO,
    Suggestion,
    SuggestionContent,
    FileDTO
)
from app.chat.api.dto import Attachment as AttachmentDTO
from app.chat.api.stream_models import (
    ArtifactBlock,
    ArtifactBlockStartEvent,
    ArtifactBlockStopEvent,
    ReferenceBlock,
    ReferenceBlockStartEvent,
    ReferenceBlockStopEvent,

    ContentBlock,
    ContentBlockDeltaEvent,
    ContentBlockStartEvent,
    ContentBlockStopEvent,
    ErrorData,
    ErrorEvent,
    MessageDeltaData,
    MessageDeltaEvent,
    MessageLimit,
    MessageLimitEvent,
    MessageMetadata,
    MessageStartEvent,
    MessageStopEvent,
    StopResponseResult,
    SuggestionBlock,
    SuggestionBlockStartEvent,
    SuggestionBlockStopEvent,
    TextDelta,
    MetaContent,
    MetaContentEvent,
    DataSummaryDeltaEvent,
)
from app.chat.entity.chat import Artifact as ArtifactEntity, Reference as ReferenceEntity
from app.chat.entity.chat import Attachment, Conversation
from app.chat.entity.chat import CompletionRequest as CompletionRequestEntity
from app.chat.entity.chat import Suggestion as SuggestionEntity
from app.chat.entity.chat import SuggestionContent as SuggestionContentEntity, File
from app.chat.service.chat_service import ChatService
from app.chat.service.completion_service import ChatCompletionService
from pkg.log.logger import Logger


class ChatHandler:
    """Handler class for chat-related HTTP endpoints."""

    def __init__(self, chat_service: ChatService,  logger: Logger, completion_service: ChatCompletionService ):
        self._service = chat_service
        self.completion_service = completion_service
        self._logger = logger
        self._active_streams: dict[UUID, asyncio.Task] = {}

    async def get_pals(self) -> list[PAL]:
        return [
            PAL(
                id="1",
                name="Analytics",
                pal_enum="ANALYST_PAL",
                description="will help in doing analytics and visualizations",
                type="FREE_PLAN",
                image="",
                suggestions=[],
                is_active=True,
            ),
            PAL(
                id="2",
                name="Knowledge search",
                pal_enum="KNOWLEDGE_PAL",
                description="will help in finding relevant context for knowledge base",
                type="FREE_PLAN",
                image="",
                suggestions=[
                    "can you find the relevant information from docs for the given information",
                    "help me with understanding this using my documents",
                ],
                is_active=True,
            ),
            PAL(
                id="3",
                name="Order Processor",
                pal_enum="ORDER_PROCESSING",
                description="will help in processing the orders from emails and erp",
                type="ENTERPRISE_PLAN",
                image="",
                suggestions=["Process all latest orders received into the queue"],
                is_active=True,
            ),
            PAL(
                id="4",
                name="Sustainability assistant",
                pal_enum="SUSTAINABILITY_PAL",
                description="will help in doing sustainability reporting",
                type="ENTERPRISE_PLAN",
                image="",
                suggestions=[],
                is_active=True,
            ),
            PAL(
                id="5",
                name="Sourcing Assistant",
                pal_enum="SOURCING_PAL",
                description="will help in doing sourcing",
                type="FREE_PLAN",
                image="",
                suggestions=[],
                is_active=True,
            ),
            PAL(
                id="6",
                name="Market Analyser PAL",
                pal_enum="MARKET_ANALYSER",
                description="will help in doing maket analysis and insights",
                type="ENTERPRISE_PLAN",
                image="",
                suggestions=[],
                is_active=True,
            )
        ]

    async def create_conversation(self, user_id: str, conversation_data: CreateConversationRequest
    ) -> CreateConversationResponse:
        """Create a new conversation."""
        try:
            conversation = await self._service.create_conversation(
                user_id, conversation_data.id
            )
            return self._create_conversation_response(conversation)
        except Exception as e:
            self._logger.error(f"Error creating conversation: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create conversation: {e!s}"
            )

    async def list_conversations(self, user_id: str, pal: str = None) -> ListConversationsResponse:
        """List all conversations for a user."""
        try:
            conversations = await self._service.list_conversations(user_id, pal)
            return ListConversationsResponse(
                conversations=[
                    self._convert_to_conversation_dto(conv) for conv in conversations
                ]
            )
        except Exception as e:
            self._logger.error(f"Error listing conversations: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Failed to list conversations: {e!s}"
            )

    async def get_conversation(self, user_id: str, conversation_id: UUID) -> GetConversationResponse:
        """Get a conversation by ID with its messages."""
        try:
            conversation = await self._service.get_conversation(user_id, conversation_id)
            return self._create_get_conversation_response(conversation)
        except ValueError as e:
            print("error", e)
            raise HTTPException(status_code=404, detail=str(e))
        except Exception as e:
            self._logger.error(f"Error getting conversation: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Failed to get conversation: {e!s}"
            )

    async def stop_stream(self, conversation_id: UUID) -> StopResponseResult:
        """Stop an active stream for a conversation."""
        try:
            stream_task = self._active_streams.get(conversation_id)
            if stream_task and not stream_task.done():
                await self._stop_stream_task(stream_task)
                self._active_streams.pop(conversation_id, None)
            return StopResponseResult(stop_id=conversation_id)
        except Exception as e:
            self._logger.error(f"Error stopping stream: {e!s}")
            raise HTTPException(status_code=500, detail=f"Failed to stop stream: {e!s}")

    async def stream_completion(self, user_id: str, conversation_id: UUID,
                                completion_request: CompletionRequest) -> StreamingResponse:
        """Stream a chat completion response."""
        try:
            entity_request = self._convert_to_completion_request_entity(completion_request)

            # Create a queue to manage the stream
            queue = asyncio.Queue()

            async def stream_processor():
                try:
                    message_id = f"chatcompl_{uuid4().hex[:24]}"
                    message_uuid = uuid4()

                    await queue.put(
                        self._create_message_start_event(
                            message_id, message_uuid, completion_request
                        )
                    )
                    await queue.put(self._create_content_block_start_event())

                    async for chunk in self.completion_service.create_completion(
                            user_id, conversation_id, entity_request
                    ):
                        if isinstance(chunk, dict):
                            if chunk.get("type") == "suggestions":
                                await queue.put(
                                    self._create_suggestion_events(chunk["suggestions"])
                                )
                            elif chunk.get("type") == "artifacts":
                                print("artifacts")
                                await queue.put(
                                    self._create_artifact_events(chunk["artifacts"])
                                )
                            elif chunk.get("type") == "references":
                                await queue.put(
                                    self._convert_reference_events(chunk["references"])
                                )
                            elif chunk.get("type") == "meta_content":
                                await queue.put(
                                    self._create_meta_content_events(chunk["meta_content"])
                                )

                            elif chunk.get("type") == "data_summary_delta":
                                await queue.put(
                                    self._create_data_summary_delta_event(chunk["data_summary_delta"])
                                )
                        elif chunk:
                            await queue.put(self._create_content_delta_event(chunk))

                    # Send completion end events
                    for event in self._create_completion_end_events(False):
                        await queue.put(event)

                except asyncio.CancelledError:
                    for event in self._create_completion_end_events(True):
                        await queue.put(event)
                    raise
                except Exception as e:
                    self._logger.error(f"Error in stream processor: {e!s}")
                    await queue.put(self._create_error_event(str(e)))
                finally:
                    self._active_streams.pop(conversation_id, None)
                    await queue.put(None)  # Signal stream end

            async def stream_generator():
                try:
                    # Start the processor task
                    processor_task = asyncio.create_task(stream_processor())
                    self._active_streams[conversation_id] = processor_task

                    # Yield chunks from the queue until we get None
                    while True:
                        chunk = await queue.get()
                        if chunk is None:
                            break
                        yield chunk
                except asyncio.CancelledError:
                    if conversation_id in self._active_streams:
                        await self._stop_stream_task(
                            self._active_streams[conversation_id]
                        )
                    raise
                finally:
                    # Ensure the processor task is cleaned up
                    if conversation_id in self._active_streams:
                        await self._stop_stream_task(
                            self._active_streams[conversation_id]
                        )

            return StreamingResponse(
                stream_generator(),
                media_type="text/event-stream",
                headers=self._get_stream_headers(),
            )
        except Exception as e:
            self._logger.error(f"Error creating stream: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Failed to create stream: {e!s}"
            )

    async def extract_file(self, request: FileExtractRequest) -> FileExtractResponse:
        """Extract content from a file."""
        try:
            response = await self._service.extract_file(
                request.file_content, request.file_name
            )
            return FileExtractResponse(
                extracted_content=response.extracted_content,
                file_name=response.file_name,
                file_type=response.file_type,
                file_size=response.file_size,
            )
        except Exception as e:
            self._logger.error(f"Error extracting file: {e!s}")
            raise HTTPException(
                status_code=500, detail=f"Failed to extract file: {e!s}"
            )

    async def get_message(self, user_id: str, message_id: str) -> MessageDTO:
        """Get a message by ID.
        
        Args:
            user_id: The ID of the user requesting the message
            message_id: The UUID of the message to retrieve
            
        Returns:
            MessageDTO: The message if found and accessible
            
        Raises:
            HTTPException: If the message is not found or access is denied
        """
        try:
            message = await self._service.get_message(user_id=user_id, message_id=UUID(message_id))
            if not message:
                raise HTTPException(
                    status_code=404,
                    detail=f"Message {message_id} not found or access denied"
                )
            return self._convert_to_message_dto(message)
        except ValueError as e:
            raise HTTPException(status_code=400, detail="Invalid message ID format")
        except Exception as e:
            self._logger.error(f"Error getting message: {e!s}")
            raise HTTPException(
                status_code=500,
                detail=f"Failed to get message: {e!s}"
            )

    # Private helper methods
    def _create_conversation_response(
            self, conversation: Conversation
    ) -> CreateConversationResponse:
        """Create a response DTO for a new conversation."""
        return CreateConversationResponse(
            id=conversation.id,
            name=conversation.name,
            model=conversation.model,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            is_starred=conversation.is_starred,
            current_leaf_message_id=conversation.current_leaf_message_id,
        )

    def _create_get_conversation_response(self, conversation: Conversation) -> GetConversationResponse:
        """Create a response DTO for getting a conversation."""
        return GetConversationResponse(
            id=conversation.id,
            name=conversation.name,
            model=conversation.model,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            is_starred=conversation.is_starred,
            current_leaf_message_id=conversation.current_leaf_message_id,
            chat_messages=[
                self._convert_to_message_dto(message)
                for message in conversation.messages
            ],
        )

    def _convert_to_conversation_dto(self, conversation: Conversation) -> ConversationDTO:
        """Convert a conversation entity to DTO."""
        return ConversationDTO(
            id=conversation.id,
            name=conversation.name,
            model=conversation.model,
            created_at=conversation.created_at,
            updated_at=conversation.updated_at,
            is_starred=conversation.is_starred,
            current_leaf_message_id=conversation.current_leaf_message_id,
        )

    def _convert_to_message_dto(self, message: Any) -> MessageDTO:
        """Convert a message entity to DTO."""
        return MessageDTO(
            id=message.id,
            role=message.role,
            content=message.content,
            conversation_id=message.conversation_id,
            parent_message_id=message.parent_message_id,
            model=message.model,
            database_uid=message.database_uid,
            table_uid=message.table_uid,
            files=self._convert_files_to_dto(message.files),
            suggestions=self._convert_suggestions_to_dto(message.suggestions),
            attachments=self._convert_attachments_to_dto(message.attachments),
            artifacts=self._convert_artifacts_to_dto(message.artifacts),
            references=self._convert_references_to_dto(message.references),
            stop_reason=message.stop_reason,
            stop_sequence=message.stop_sequence,
            created_at=message.created_at,
            index=message.index,
            sender=message.role.value,
            metadata=message.meta_data,
        )

    def _convert_to_completion_request_entity(self, request: CompletionRequest) -> CompletionRequestEntity:
        """Convert a completion request DTO to entity."""
        return CompletionRequestEntity(
            prompt=request.prompt,
            parent_message_id=request.parent_message_id,
            attachments=[
                self.model_attachment_dto_to_entity(attachment) for attachment in request.attachments
            ],
            selected_suggestions=[
                SuggestionEntity(
                    type=suggestion.type,
                    suggestion_content=SuggestionContentEntity(
                        title=suggestion.suggestion_content.title,
                        type=suggestion.suggestion_content.type,
                        source_url=suggestion.suggestion_content.source_url,
                        uploaded_by=suggestion.suggestion_content.uploaded_by,
                        description=suggestion.suggestion_content.description,
                        text=suggestion.suggestion_content.text,
                    ),
                )
                for suggestion in request.selected_suggestions
            ],
            files=[self.model_attachment_dto_to_file(file) for file in request.files],
            rendering_mode=request.rendering_mode,
            sync_sources=request.sync_sources,
            timezone=request.timezone,
            model=request.model,
            web_search=request.web_search,
            knowledge_search=request.knowledge_search,
            database_uid=request.database_uid,
            table_uid=request.table_uid,
        )

    def model_attachment_dto_to_entity(self, attachment: AttachmentDTO) -> Attachment:
        return Attachment(title=attachment.file_name, type=attachment.file_type,
                          extracted_content=attachment.extracted_content, file_size=attachment.file_size)

    def model_attachment_dto_to_file(self, file: FileDTO) -> File:
        return File(title=file.title, content=file.content, address=file.address, id=file.id)

    async def _stop_stream_task(self, task: asyncio.Task):
        """Safely stop a stream task."""
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass

    def _get_stream_headers(self) -> dict[str, str]:
        """Get headers for streaming response."""
        return {
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "Content-Type": "text/event-stream",
            "X-Accel-Buffering": "no",
        }

    def _convert_suggestions_to_dto(self, suggestions: list[Any]) -> list[Suggestion]:
        """Convert suggestions to DTOs."""
        return [
            Suggestion(
                type=s.type,
                suggestion_content=SuggestionContent(
                    type=s.suggestion_content.type,
                    title=s.suggestion_content.title,
                    source_url=s.suggestion_content.source_url,
                    description=s.suggestion_content.description,
                    uploaded_by=s.suggestion_content.uploaded_by,
                    text=s.suggestion_content.text,
                ),
            )
            for s in suggestions
        ]

    def _convert_attachments_to_dto(self, attachments: list[Any]) -> list[AttachmentDTO]:
        """Convert attachments to DTOs."""
        return [
            AttachmentDTO(
                file_name=attachment.title,
                file_size=attachment.file_size,
                file_type=attachment.type,
                extracted_content=attachment.extracted_content,
            )
            for attachment in attachments
        ]

    def _create_message_start_event(self, message_id: str, message_uuid: UUID,
                                    completion_request: CompletionRequestEntity) -> str:
        """Create a message start event."""
        event = MessageStartEvent(
            type="message_start",
            message=MessageMetadata(
                id=message_id,
                type="message",
                role="assistant",
                model="gpt-4o-mini",
                parent_uuid=completion_request.parent_message_id,
                uuid=message_uuid,
                content=[],
                stop_reason=None,
                stop_sequence=None,
            ),
        )
        return f"event: message_start\ndata: {event.model_dump_json()}\n\n"

    def _create_content_block_start_event(self) -> str:
        """Create a content block start event."""
        event = ContentBlockStartEvent(
            type="content_block_start",
            index=0,
            content_block=ContentBlock(type="text", text=""),
        )
        return f"event: content_block_start\ndata: {event.model_dump_json()}\n\n"

    def _create_content_delta_event(self, chunk: str) -> str:
        """Create a content delta event."""
        event = ContentBlockDeltaEvent(
            type="content_block_delta",
            index=0,
            delta=TextDelta(type="text_delta", text=chunk),
        )
        return f"event: content_block_delta\ndata: {event.model_dump_json()}\n\n"

    def _create_suggestion_events(self, suggestions: list[Any]) -> str:
        """Create suggestion block events."""
        start_event = SuggestionBlockStartEvent(
            type="suggestion_block_start",
            index=1,
            suggestion_block=SuggestionBlock(
                type="suggestions",
                suggestions=self._convert_suggestions_to_dto(suggestions),
            ),
        )
        stop_event = SuggestionBlockStopEvent(type="suggestion_block_stop", index=1)
        return (
            f"event: suggestion_block_start\ndata: {start_event.model_dump_json()}\n\n"
            f"event: suggestion_block_stop\ndata: {stop_event.model_dump_json()}\n\n"
        )

    def _create_completion_end_events(self, was_cancelled: bool) -> list[str]:
        """Create events for completion end."""
        events = []

        # Content block stop
        content_block_stop = ContentBlockStopEvent(type="content_block_stop", index=0)
        events.append(
            f"event: content_block_stop\ndata: {content_block_stop.model_dump_json()}\n\n"
        )

        # Message delta
        message_delta = MessageDeltaEvent(
            type="message_delta",
            delta=MessageDeltaData(
                stop_reason="user_canceled" if was_cancelled else "end_turn",
                stop_sequence=None,
            ),
        )
        events.append(
            f"event: message_delta\ndata: {message_delta.model_dump_json()}\n\n"
        )

        # Message limit
        message_limit = MessageLimitEvent(
            type="message_limit", message_limit=MessageLimit(type="within_limit")
        )
        events.append(
            f"event: message_limit\ndata: {message_limit.model_dump_json()}\n\n"
        )

        # Message stop
        message_stop = MessageStopEvent(type="message_stop")
        events.append(
            f"event: message_stop\ndata: {message_stop.model_dump_json()}\n\n"
        )

        return events

    def _create_error_event(self, error_message: str) -> str:
        """Create an error event."""
        error_event = ErrorEvent(
            type="error", error=ErrorData(message=error_message, type="stream_error")
        )
        return f"event: error\ndata: {error_event.model_dump_json()}\n\n"

    def _create_artifact_events(self, artifacts: list[ArtifactEntity]) -> str:
        """Create artifact block events."""
        start_event = ArtifactBlockStartEvent(
            type="artifact_block_start",
            index=2,
            artifact_block=ArtifactBlock(
                type="artifacts", artifacts=self._convert_artifacts_to_dto(artifacts)
            ),
        )
        stop_event = ArtifactBlockStopEvent(type="artifact_block_stop", index=2)
        return (
            f"event: artifact_block_start\ndata: {start_event.model_dump_json()}\n\n"
            f"event: artifact_block_stop\ndata: {stop_event.model_dump_json()}\n\n"
        )

    def _convert_reference_events(self, references: list[ReferenceEntity]) -> str:
        start_event = ReferenceBlockStartEvent(
            type="reference_block_start",
            index=3,
            reference_block=ReferenceBlock(
                type="references", references=self._convert_references_to_dto(references)
            ),
        )
        stop_event = ReferenceBlockStopEvent(type="reference_block_stop", index=2)
        return (
            f"event: reference_block_start\ndata: {start_event.model_dump_json()}\n\n"
            f"event: reference_block_stop\ndata: {stop_event.model_dump_json()}\n\n"
        )

    def _convert_references_to_dto(self, references: list[Any]) -> list[Any]:
        """Convert references to DTOs."""
        return [
            Reference(
                type=reference.type,
                title=reference.title,
                content=reference.content,
                address=reference.address,
            )
            for reference in references
        ]

    def _create_meta_content_events(self, meta_content: dict) -> str:
        """Create meta content block events."""
        # Create MetaContent model from the dictionary
        meta_content_model = MetaContent(
            id=meta_content.get("id", str(uuid4())),
            title=meta_content.get("title", ""),
            status=meta_content.get("status", ""),
            type=meta_content.get("type", "text"),
            description=meta_content.get("description", [])
        )

        meta_content_event = MetaContentEvent(
            type="meta_content",
            index=4,
            meta_content=meta_content_model
        )

        # Return formatted events
        return (
            f"event: meta_content\ndata: {meta_content_event.model_dump_json()}\n\n"
        )

    def _create_data_summary_delta_event(self, data_summary_delta: dict) -> str:
        """Create a data summary delta event."""
        event = DataSummaryDeltaEvent(type="data_summary_delta", delta=data_summary_delta)
        return f"event: data_summary_delta\ndata: {event.model_dump_json()}\n\n"

    def _convert_artifacts_to_dto(
            self, artifacts: list[ArtifactEntity]
    ) -> list[Artifact]:
        """Convert artifacts to DTOs."""
        return [
            Artifact(
                artifact_type=artifact.artifact_type,
                content=artifact.content,
                language=artifact.language,
                title=artifact.title,
                file_type=artifact.file_type,
            )
            for artifact in artifacts
        ]

    def _convert_files_to_dto(self, files: list[File]) -> list[FileDTO]:
        """Convert files to DTOs."""
        return [
            FileDTO(
                id=file.id,
                title=file.title,
                content=file.content,
                address=file.address,
            )
            for file in files
        ]

    async def _run_stream(self, generator: AsyncIterator[str]) -> None:
        """Run the stream generator."""
        try:
            async for _ in generator:
                pass
        except asyncio.CancelledError:
            # Handle cancellation gracefully
            pass