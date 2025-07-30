from typing import List, Optional, Dict, Any, Union
from datetime import datetime, timezone
import asyncio
from concurrent.futures import ThreadPoolExecutor
import uuid
import orjson

from sqlalchemy import select, insert, update, delete, and_, or_, func, desc
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from pkg.log.logger import Logger
from pkg.db_util.postgres_conn import PostgresConnection
from app.chat.entity.chat import (
    Message as MessageEntity, Conversation as ConversationEntity,
    Document, CodeSnippet, Role, Artifact, Attachment, Suggestion, File, Reference
)
from app.chat.repository.sql_schema.conversation import ConversationModel, MessageModel
from app.chat.service.service import IChatRepository



class ChatRepository(IChatRepository):
    def __init__(self, db_conn: PostgresConnection, logger: Logger):
        self.logger = logger
        self.db_conn = db_conn
        self.thread_pool = ThreadPoolExecutor()

    async def save_conversation(self, user_id: str, conversation: ConversationEntity) -> uuid.UUID:
        """Save or update a conversation"""
        try:
            # Set default model if None is provided
            if conversation.model is None:
                conversation.model = None # Use appropriate default model name
                
            async with self.db_conn.get_session() as session:
                # Begin transaction
                await session.begin()
                
                try:
                    # Check if conversation exists and belongs to the user
                    stmt = select(ConversationModel).where(
                        and_(
                            ConversationModel.id == conversation.id,
                            ConversationModel.user_id == user_id
                        )
                    )
                    result = await session.execute(stmt)
                    existing_conversation = result.scalars().first()
                    
                    # Update meta_data if it exists
                    meta_data = conversation.meta_data
                    
                    if existing_conversation:
                        # Update existing conversation
                        update_values = {
                            "name": conversation.name,
                            "model": conversation.model,
                            "updated_at": datetime.now(timezone.utc),
                            "last_activity_at": conversation.last_activity,
                            "meta_data": meta_data
                        }
                        
                        update_stmt = (
                            update(ConversationModel)
                            .where(ConversationModel.id == conversation.id)
                            .values(**update_values)
                        )
                        
                        await session.execute(update_stmt)
                    else:
                        # Create new conversation
                        new_conversation = ConversationModel(
                            id=conversation.id,
                            user_id=user_id,
                            name=conversation.name,
                            model=conversation.model,
                            created_at=conversation.created_at,
                            updated_at=conversation.updated_at,
                            last_activity_at=conversation.last_activity,
                            meta_data=meta_data
                        )
                        
                        session.add(new_conversation)
                    
                    # Commit transaction
                    await session.commit()
                    return conversation.id
                    
                except Exception as e:
                    # Rollback on error
                    await session.rollback()
                    raise e

        except Exception as e:
            self.logger.error(f"Error saving conversation: {str(e)}", exc_info=True)
            raise e

    async def save_message(self, user_id: str, message: MessageEntity) -> uuid.UUID:
        """Save a message"""
        try:
            async with self.db_conn.get_session() as session:
                # Begin transaction
                await session.begin()
                
                try:
                    # First check if conversation exists and belongs to the user
                    stmt = select(ConversationModel).where(
                        and_(
                            ConversationModel.id == message.conversation_id,
                            ConversationModel.user_id == user_id
                        )
                    )
                    result = await session.execute(stmt)
                    conversation = result.scalars().first()
                    
                    if not conversation:
                        raise Exception(f"Conversation {message.conversation_id} not found or access denied")
                    
                    # Convert entity to model
                    message_model = MessageModel.from_entity(message)
                    
                    # Add to session
                    session.add(message_model)

                    update_stmt = (
                        update(ConversationModel)
                        .where(ConversationModel.id == message.conversation_id)
                        .values(
                            current_leaf_message_id=message.id,
                            model=message.model,
                            updated_at=datetime.now(timezone.utc)
                        )
                    )
                    await session.execute(update_stmt)
                    
                    # Commit transaction
                    await session.commit()
                    
                except Exception as e:
                    # Rollback on any error
                    await session.rollback()
                    raise e
                
                return message.id
        except Exception as e:
            self.logger.error(f"Error saving message: {str(e)}", exc_info=True)
            raise e

    async def get_conversation(self, user_id: str,conversation_id: uuid.UUID,
                               include_messages: bool = True, page: int = 1,
                               page_size: int = 100000) -> Optional[ConversationEntity]:
        """Get a conversation by ID with pagination for messages"""
        try:
            async with self.db_conn.get_session() as session:
                # First verify the user has access to this conversation
                access_stmt = select(ConversationModel).where(
                    and_(
                        ConversationModel.id == conversation_id,
                        ConversationModel.user_id == user_id
                    )
                )
                
                access_result = await session.execute(access_stmt)
                conversation = access_result.scalars().first()
                
                if not conversation:
                    return None
                
                # Convert to entity
                conversation_entity = conversation.to_entity()
                
                # Add messages if included, with pagination
                if include_messages:
                    # Calculate offset
                    offset = (page - 1) * page_size
                    
                    # Query messages with pagination
                    messages_stmt = (
                        select(MessageModel)
                        .where(MessageModel.conversation_id == conversation_id)
                        .order_by(MessageModel.created_at)
                        .offset(offset)
                        .limit(page_size)
                    )
                    
                    messages_result = await session.execute(messages_stmt)
                    messages = messages_result.scalars().all()
                    
                    # Convert to entities
                    message_entities = [message.to_entity() for message in messages]
                    conversation_entity.messages = message_entities
                
                return conversation_entity
                
        except Exception as e:
            self.logger.error(f"Error getting conversation {conversation_id}: {str(e)}", exc_info=True)
            raise e

    async def list_conversations(self, user_id: str, pal: Optional[str] = None) -> List[ConversationEntity]:
        """List all conversations for a user"""
        try:
            async with self.db_conn.get_session() as session:
                # Build query with filters
                query = select(ConversationModel).where(ConversationModel.user_id == user_id)
                
                if pal:
                    query = query.where(ConversationModel.model == pal)
                
                # Add ordering
                query = query.order_by(desc(ConversationModel.created_at))
                
                result = await session.execute(query)
                conversations = result.scalars().all()
                
                # Convert to entities
                conversation_entities = []
                for conv in conversations:
                    conversation_entity = conv.to_entity()
                    conversation_entities.append(conversation_entity)
                
                return conversation_entities
                
        except Exception as e:
            self.logger.error(f"Error listing conversations: {str(e)}", exc_info=True)
            raise e

    async def get_message(self, user_id: str, message_id: uuid.UUID ) -> MessageEntity:
        """Get a message by ID with user access check"""
        try:
            async with self.db_conn.get_session() as session:
                # Query message joined with conversation to check user access
                stmt = (
                    select(MessageModel)
                    .join(
                        ConversationModel, 
                        MessageModel.conversation_id == ConversationModel.id
                    )
                    .where(
                        and_(
                            MessageModel.id == message_id,
                            ConversationModel.user_id == user_id #TODO: Update this logic, in dashboard a different user_id can be used but still we need the message
                        )
                    )
                )
                
                result = await session.execute(stmt)
                message = result.scalars().first()
                
                if not message:
                    self.logger.error(f"Error getting message {user_id}")
                    raise Exception(f"Message {message_id} not found or access denied, {user_id}")
                
                return message.to_entity()

        except Exception as e:
            self.logger.error(f"Error getting message: {str(e)}", exc_info=True)
            raise e

    async def delete_conversation(self, conversation_id: uuid.UUID, user_id: str) -> None:
        """Delete a conversation and all related messages with user access check"""
        try:
            async with self.db_conn.get_session() as session:
                # Begin transaction
                await session.begin()
                
                try:
                    # Check if conversation exists and belongs to the user
                    conv_stmt = select(ConversationModel).where(
                        and_(
                            ConversationModel.id == conversation_id,
                            ConversationModel.user_id == user_id
                        )
                    )
                    result = await session.execute(conv_stmt)
                    conversation = result.scalars().first()
                    
                    if not conversation:
                        raise Exception(f"Conversation {conversation_id} not found or access denied")
                    
                    # Delete the conversation (cascade will delete messages)
                    delete_stmt = delete(ConversationModel).where(ConversationModel.id == conversation_id)
                    await session.execute(delete_stmt)
                    
                    # Commit transaction
                    await session.commit()
                    
                except Exception as e:
                    # Rollback on any error
                    await session.rollback()
                    raise e

        except Exception as e:
            self.logger.error(f"Error deleting conversation: {str(e)}", exc_info=True)
            raise e

    async def update_conversation_model(self, user_id: str, conversation_id: uuid.UUID,
                                      conversation_model: str) -> ConversationEntity:
        """Update the model of a conversation"""
        try:
            async with self.db_conn.get_session() as session:
                # Begin transaction
                await session.begin()
                
                try:
                    # Verify user has access to the conversation
                    access_stmt = select(ConversationModel).where(
                        and_(
                            ConversationModel.id == conversation_id,
                            ConversationModel.user_id == user_id
                        )
                    )
                    access_result = await session.execute(access_stmt)
                    
                    if not access_result.scalars().first():
                        raise Exception(f"Conversation {conversation_id} not found or access denied")
                    
                    # Update the conversation model
                    update_stmt = (
                        update(ConversationModel)
                        .where(ConversationModel.id == conversation_id)
                        .values(model=conversation_model)
                        .returning(ConversationModel)
                    )
                    
                    result = await session.execute(update_stmt)
                    updated_conversation = result.scalars().first()
                    
                    if not updated_conversation:
                        raise Exception(f"Conversation {conversation_id} not found")
                    
                    # Commit transaction
                    await session.commit()
                    
                    return updated_conversation.to_entity()
                    
                except Exception as e:
                    # Rollback on error
                    await session.rollback()
                    raise e

        except Exception as e:
            self.logger.error(f"Error updating conversation model: {str(e)}", exc_info=True)
            raise e

    async def update_conversation_name(self, user_id: str, conversation_id: uuid.UUID, name: str) -> ConversationEntity:
        """Update the name of a conversation"""
        try:
            async with self.db_conn.get_session() as session:
                # Begin transaction
                await session.begin()
                
                try:
                    # Verify user has access to the conversation
                    access_stmt = select(ConversationModel).where(
                        and_(
                            ConversationModel.id == conversation_id,
                            ConversationModel.user_id == user_id
                        )
                    )
                    access_result = await session.execute(access_stmt)
                    
                    if not access_result.scalars().first():
                        raise Exception(f"Conversation {conversation_id} not found or access denied")
                    
                    # Update the conversation name
                    update_stmt = (
                        update(ConversationModel)
                        .where(ConversationModel.id == conversation_id)
                        .values(name=name)
                        .returning(ConversationModel)
                    )
                    
                    result = await session.execute(update_stmt)
                    updated_conversation = result.scalars().first()
                    
                    if not updated_conversation:
                        raise Exception(f"Conversation {conversation_id} not found")
                    
                    # Commit transaction
                    await session.commit()
                    
                    return updated_conversation.to_entity()
                    
                except Exception as e:
                    # Rollback on error
                    await session.rollback()
                    raise e

        except Exception as e:
            self.logger.error(f"Error updating conversation name: {str(e)}", exc_info=True)
            raise e

    async def get_messages_by_conversation_id(self, conversation_id: uuid.UUID, 
                                             limit: int = 50, 
                                             offset: int = 0) -> List[MessageEntity]:
        """Get messages for a specific conversation with pagination"""
        try:
            async with self.db_conn.get_session() as session:
                # Check if conversation exists
                conv_stmt = select(ConversationModel).where(ConversationModel.id == conversation_id)
                conv_result = await session.execute(conv_stmt)
                conversation = conv_result.scalars().first()
                
                if not conversation:
                    raise Exception(f"Conversation {conversation_id} not found")
                
                # Query messages with pagination
                stmt = (
                    select(MessageModel)
                    .where(MessageModel.conversation_id == conversation_id)
                    .order_by(MessageModel.index)
                    .offset(offset)
                    .limit(limit)
                )
                
                result = await session.execute(stmt)
                messages = result.scalars().all()
                
                # Convert to entities
                message_entities: List[MessageEntity] = [message.to_entity() for message in messages]
                
                return message_entities

        except Exception as e:
            self.logger.error(f"Error getting messages for conversation {conversation_id}: {str(e)}", exc_info=True)
            raise e

    async def bulk_save_messages(self, user_id: str, messages: List[MessageEntity]) -> List[uuid.UUID]:
        """Save multiple messages in a single transaction"""
        if not messages:
            return []
            
        try:
            async with self.db_conn.get_session() as session:
                # Begin transaction
                await session.begin()
                
                try:
                    # Group messages by conversation for validation
                    conversation_ids = {msg.conversation_id for msg in messages}
                    
                    # Verify all conversations exist and belong to the user
                    for conv_id in conversation_ids:
                        stmt = select(ConversationModel).where(
                            and_(
                                ConversationModel.id == conv_id,
                                ConversationModel.user_id == user_id
                            )
                        )
                        result = await session.execute(stmt)
                        conversation = result.scalars().first()
                        
                        if not conversation:
                            raise Exception(f"Conversation {conv_id} not found or access denied")
                    
                    # Convert entities to models and add to session
                    message_models = []
                    message_ids = []
                    
                    for message in messages:
                        message_model = MessageModel.from_entity(message)
                        session.add(message_model)
                        message_models.append(message_model)
                        message_ids.append(message.id)
                    
                    # Update the current_leaf_message_id for each conversation
                    # We use the last message in each conversation as the leaf
                    for conv_id in conversation_ids:
                        # Find the last message in this conversation
                        conv_messages = [msg for msg in messages if msg.conversation_id == conv_id]
                        if conv_messages:
                            # Sort by index to get the last message
                            last_message = max(conv_messages, key=lambda m: m.index)
                            
                            # Update the conversation
                            update_stmt = (
                                update(ConversationModel)
                                .where(ConversationModel.id == conv_id)
                                .values(
                                    current_leaf_message_id=last_message.id,
                                    updated_at=datetime.now(timezone.utc),
                                    last_activity_at=datetime.now(timezone.utc)
                                )
                            )
                            await session.execute(update_stmt)
                    
                    # Commit the transaction
                    await session.commit()
                    return message_ids
                    
                except Exception as e:
                    # Rollback on any error
                    await session.rollback()
                    raise e
                

        except Exception as e:
            self.logger.error(f"Error bulk saving messages: {str(e)}", exc_info=True)
            raise e
            
    async def update_message_content(self, message_id: uuid.UUID, content: str, user_id: str) -> MessageEntity:
        """Update the content of an existing message with user access check"""
        try:
            async with self.db_conn.get_session() as session:
                # Begin transaction
                await session.begin()
                
                try:
                    # Check if message exists and belongs to the user
                    access_stmt = (
                        select(MessageModel)
                        .join(
                            ConversationModel, 
                            MessageModel.conversation_id == ConversationModel.id
                        )
                        .where(
                            and_(
                                MessageModel.id == message_id,
                                ConversationModel.user_id == user_id
                            )
                        )
                    )
                    access_result = await session.execute(access_stmt)
                    message = access_result.scalars().first()
                    
                    if not message:
                        raise Exception(f"Message {message_id} not found or access denied")
                    
                    # Update message content
                    update_stmt = (
                        update(MessageModel)
                        .where(MessageModel.id == message_id)
                        .values(content=content)
                        .returning(MessageModel)
                    )
                    
                    result = await session.execute(update_stmt)
                    updated_message = result.scalars().first()
                    
                    # Commit transaction
                    await session.commit()
                    
                    return updated_message.to_entity()
                    
                except Exception as e:
                    # Rollback on any error
                    await session.rollback()
                    raise e

        except Exception as e:
            self.logger.error(f"Error updating message content: {str(e)}", exc_info=True)
            raise e
