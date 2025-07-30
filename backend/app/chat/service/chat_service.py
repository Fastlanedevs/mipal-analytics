import uuid
from typing import List, Optional, Dict, Any, Union, Tuple
from uuid import uuid4
from uuid import UUID
from datetime import datetime, timezone
import asyncio
import json
import io
from fastapi import HTTPException
from app.chat.service.util import extract_file_content

# Import necessary modules
from app.chat.service.service import IChatRepository, ILLMAdapter
from app.chat.entity.chat import (Conversation, Message, CompletionRequest, FileExtract,
                                  Suggestion, Artifact, Reference, Role)
from pkg.log.logger import Logger
from pkg.redis.client import RedisClient

class ChatService:
    """Service class handling chat-related business logic with performance optimizations."""

    def __init__(self, chat_repository: IChatRepository, logger: Logger,
                 redis_client: RedisClient, llm_adapter: ILLMAdapter):
        """Initialize the ChatService with configurable dependencies."""

        # Legacy initialization
        self.chat_repository: IChatRepository = chat_repository
        self.logger: Logger = logger
        self.redis_client = redis_client
        self.llm_adapter = llm_adapter

        # Store new dependencies

        # Set timeout for external calls
        self._external_call_timeout = 120  # seconds

    async def create_conversation(self, user_id: str, conversation_id: UUID,
                                  model: Optional[str] = None) -> Conversation:
        self.logger.info(f"Creating new conversation for user {user_id} with id {conversation_id}")
        try:
            conversation = Conversation(
                id=conversation_id,
                name= "New Conversation",
                user_id=user_id,
                model=model,
                created_at=datetime.now(timezone.utc),
                updated_at=datetime.now(timezone.utc),
                last_activity=datetime.now(timezone.utc)
            )
            result = await self.chat_repository.save_conversation(user_id, conversation)
                
            self.logger.info(f"Successfully created conversation {conversation_id} for user {user_id}")
            return conversation
        except Exception as e:
            self.logger.error(f"Failed to create conversation for user {user_id}: {str(e)}")
            raise e

    async def get_conversation(self, user_id: str, conversation_id: UUID, include_messages=True) -> Conversation:
        """Get conversation by ID with improved error handling and Redis caching"""
        try:

            # Fetch from repository
            conversation = await self.chat_repository.get_conversation(user_id, conversation_id, include_messages)
            if not conversation:
                raise ValueError(f"Conversation {conversation_id} not found for user {user_id}")
            return conversation

        except Exception as e:
            self.logger.error(f"Error retrieving conversation {conversation_id} for user {user_id}: {str(e)}")
            raise e


    async def list_conversations(self, user_id: str, pal: str = None) -> List[Conversation]:
        return await self.chat_repository.list_conversations(user_id, pal)

    async def add_message(self, user_id: str, conversation_id: UUID, message: Message) -> Message:
        message.conversation_id = conversation_id
        # Check if parent_message_id is valid
        if not message.parent_message_id or message.parent_message_id == uuid.UUID(int=0):
            message.parent_message_id = None  # or set to a default value if needed

        await self.chat_repository.save_message(user_id, message)

        
        return message

    async def update_conversation_title(self, conversation: Conversation, user_id: str, conversation_id: UUID):
        """More efficient conversation title generation"""
        # Use StringIO instead of string concatenation
        content_buffer = io.StringIO()
        # Limit to first 3 messages only
        messages_to_process = conversation.messages
        for message in messages_to_process:
            # Only take first 200 chars of each message
            content_buffer.write(message.content[:500])
            content_buffer.write("\n")

        content = content_buffer.getvalue()
        # Limit total content to process
        title = await self.llm_adapter.get_completion(content[:10000])
        conversation.name = title
        await self.chat_repository.update_conversation_name(user_id, conversation_id, conversation.name)
        


    async def extract_file(self, file_content: bytes, file_name: str = "") -> FileExtract:
        """Extract content from file with timeout protection"""
        self.logger.info(f"Extracting content from file: {file_name}, size: {len(file_content)} bytes")
        try:
            # Add timeout for external processing
            async with asyncio.timeout(self._external_call_timeout):
                extracted_text, file_type = await extract_file_content(file_content, file_name, self.llm_adapter)

            self.logger.info(f"Successfully extracted content from file {file_name} of type {file_type}")
            return FileExtract(
                file_name=file_name,
                file_size=len(file_content),
                file_type=file_type,
                extracted_content=extracted_text
            )
        except asyncio.TimeoutError:
            self.logger.error(f"Timeout extracting content from file {file_name}")
            raise HTTPException(status_code=408, detail="File processing timed out")
        except Exception as e:
            self.logger.error(f"Failed to extract content from file {file_name}: {str(e)}", exc_info=True)
            raise e

    async def create_user_message(self, conversation_id: UUID, completion_request: CompletionRequest,
                                  conversation_model: Optional[str]) -> Message:
        message = Message(
            id=uuid4(),
            role=Role.USER,
            content=completion_request.prompt,
            conversation_id=conversation_id,
            files=completion_request.files,
            parent_message_id=completion_request.parent_message_id,
            attachments=completion_request.attachments,
            suggestions=completion_request.selected_suggestions,
            model=conversation_model,
            stop_reason=None,
            created_at=datetime.now(timezone.utc),
            database_uid=completion_request.database_uid,
            table_uid=completion_request.table_uid
        )


        return message

    async def store_assistant_message(self, user_id: str, conversation_id: UUID, chunks: List[str], stop_reason: str,
                                      parent_message_id: UUID, model: Optional[str], suggestions: List[Suggestion],
                                      artifacts: List[Artifact], references: List[Reference] = None,
                                      meta_contents: List[Dict[str, Any]] = None,
                                      metadata_override: Optional[Dict[str, Any]] = None):  # Add new arg
        """Store assistant message with optimized fallback content generation and metadata override."""
        try:
            full_content = "".join(chunks) if chunks else ""
            if (not full_content or len(full_content.strip()) == 0) and artifacts:
                full_content = await self._generate_fallback_content(artifacts)
            database_uid, table_uid = await self._get_parent_message_context(user_id, parent_message_id)

            message = Message(
                id=uuid4(),
                role=Role.ASSISTANT,
                content=full_content,
                suggestions=suggestions,
                artifacts=artifacts,
                references=references,
                conversation_id=conversation_id,
                parent_message_id=parent_message_id,
                model=model,
                stop_reason=stop_reason,
                created_at=datetime.now(timezone.utc),
                database_uid=database_uid,
                table_uid=table_uid
            )

            # Apply metadata override if provided, otherwise use meta_contents
            if metadata_override is not None:
                message.meta_data = metadata_override
            elif meta_contents:
                message.meta_data["meta_contents"] = meta_contents

            await self.add_message(user_id, conversation_id, message)

        except Exception as e:
            self.logger.error(f"Failed to store assistant message: {str(e)}")


    async def _get_parent_message_context(self,user_id:str, parent_message_id: UUID) -> Tuple[Optional[str], Optional[str]]:
        """Get database context from parent message"""
        database_uid = None
        table_uid = None

        if parent_message_id:
            try:
                # Fetch from database
                parent_message = await self.chat_repository.get_message(user_id, parent_message_id)
                if parent_message:
                    database_uid = parent_message.database_uid
                    table_uid = parent_message.table_uid
            except Exception as e:
                self.logger.warning(f"Failed to get parent message for context: {str(e)}")

        return database_uid, table_uid

    async def _generate_fallback_content(self, artifacts: List['Artifact']) -> str:
        """Generate fallback content more efficiently"""
        # Use StringIO for efficient string building
        fallback = io.StringIO()
        fallback.write("# Analysis Results\n\n")

        # Get artifact types more efficiently using a set
        artifact_types = {a.artifact_type for a in artifacts}

        # Process data and metadata artifacts if present
        data_artifact = next((a for a in artifacts if a.artifact_type == "data"), None)
        metadata_artifact = next((a for a in artifacts if a.artifact_type == "metadata"), None)

        if data_artifact and metadata_artifact:
            try:
                # Parse JSON once and reuse
                data = json.loads(data_artifact.content)
                metadata = json.loads(metadata_artifact.content)

                num_rows = metadata.get("returned_rows", len(data) if isinstance(data, list) else 0)
                db_type = metadata.get("data_source", {}).get("type", "unknown")

                fallback.write(f"The analysis was performed on {num_rows} records from a {db_type} database.\n\n")
            except Exception as e:
                self.logger.warning(f"Error extracting data info for fallback content: {str(e)}")

        # Add code info if present
        code_artifact = next((a for a in artifacts if a.artifact_type == "code"), None)
        code_type_artifact = next((a for a in artifacts if a.artifact_type == "code_type"), None)
        explanation_artifact = next((a for a in artifacts if a.artifact_type == "explanation"), None)

        if code_artifact and code_type_artifact:
            code_type = code_type_artifact.content
            fallback.write(f"The analysis was performed using {code_type.upper()} code.\n\n")

            if explanation_artifact:
                fallback.write(f"**Code explanation**: {explanation_artifact.content}\n\n")

        # Add available artifacts summary
        fallback.write("## Available Analysis Artifacts\n\n")
        for artifact_type in artifact_types:
            fallback.write(f"- {artifact_type.replace('_', ' ').title()}\n")

        return fallback.getvalue()

    async def get_message(self, user_id: str, message_id: UUID) -> Optional[Message]:
        """Get a message by ID with user access check

        Args:
            user_id: The ID of the user requesting the message
            message_id: The UUID of the message to retrieve

        Returns:
            Optional[Message]: The message if found and accessible, None otherwise

        Raises:
            EntityNotFoundError: If the message is not found or access is denied
        """
        try:
            self.logger.info(f"Getting message {message_id} for user {user_id}")
            message = await self.chat_repository.get_message(user_id=user_id, message_id=message_id)
            if not message:
                self.logger.warning(f"Message {message_id} not found or access denied for user {user_id}")
                return None
            return message
        except Exception as e:
            self.logger.error(f"Error getting message {message_id}: {str(e)}")
            raise e

    async def update_conversation_model(self, user_id: str, conversation_id: UUID, model: str) -> Conversation:
        """Update the model of a conversation
        
        Args:
            user_id: The ID of the user requesting the update
            conversation_id: The UUID of the conversation to update
            model: The new model to use for the conversation
            
        Returns:
            Conversation: The updated conversation
            
        Raises:
            Exception: If the conversation is not found or access is denied
        """
        try:
            self.logger.info(f"Updating model to {model} for conversation {conversation_id} for user {user_id}")
            updated_conversation = await self.chat_repository.update_conversation_model(user_id, conversation_id, model)

            
            return updated_conversation
        except Exception as e:
            self.logger.error(f"Error updating model for conversation {conversation_id}: {str(e)}")
            raise e

    async def delete_conversation(self, user_id: str, conversation_id: UUID) -> None:
        """Delete a conversation
        
        Args:
            user_id: The ID of the user requesting the deletion
            conversation_id: The UUID of the conversation to delete
            
        Raises:
            Exception: If the conversation is not found or access is denied
        """
        try:
            self.logger.info(f"Deleting conversation {conversation_id} for user {user_id}")
            await self.chat_repository.delete_conversation(conversation_id, user_id)

            
        except Exception as e:
            self.logger.error(f"Error deleting conversation {conversation_id}: {str(e)}")
            raise e


