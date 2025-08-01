from typing import Annotated

from fastapi import APIRouter, Depends, File, UploadFile

from app.chat.api.dependency import ChatHandlerDep
from app.chat.api.dto import (
    CompletionRequest,
    CreateConversationRequest,
    FileExtractRequest,
)
from app.chat.api.stream_models import StopResponseResult
from app.middleware import get_token_detail

chat_router = APIRouter(prefix="/chat", tags=["Chat"])


@chat_router.get(
    "/conversations",
)
async def list_conversations(
    token_detail: Annotated[str, Depends(get_token_detail)],
    handler: ChatHandlerDep,
    pal: str = None
):
    return await handler.list_conversations(token_detail.user_id, pal)


@chat_router.get("/conversations/{conversation_id}")
async def get_conversation(conversation_id: str, token_detail: Annotated[str, Depends(get_token_detail)],
                           handler: ChatHandlerDep):

    return await handler.get_conversation(token_detail.user_id, conversation_id)


@chat_router.post("/conversations",)
async def create_conversation(
    request: CreateConversationRequest,
    token_detail: Annotated[str, Depends(get_token_detail)],
    handler: ChatHandlerDep,
):
    return await handler.create_conversation(token_detail.user_id, request)


@chat_router.post("/conversations/{conversation_id}/completion")
async def create_completion(
    conversation_id: str,
    request: CompletionRequest,
    token_detail: Annotated[str, Depends(get_token_detail)],
    handler: ChatHandlerDep,
):
    return await handler.stream_completion(
        token_detail.user_id, conversation_id, request
    )


@chat_router.post(
    "/conversations/{conversation_id}/stop_response", response_model=StopResponseResult
)
async def stop_response(
    conversation_id: str,
    token_detail: Annotated[str, Depends(get_token_detail)],
    handler: ChatHandlerDep,
) -> StopResponseResult:
    """Stop an ongoing stream response."""
    return await handler.stop_stream(conversation_id)


@chat_router.post("/extract")
async def extract(handler: ChatHandlerDep, file: UploadFile = File(...)):
    content = await file.read()
    request = FileExtractRequest(
        file_content=content, file_name=file.filename, mime_type=file.content_type
    )
    return await handler.extract_file(request)


@chat_router.get("/pals")
async def get_pals(handler: ChatHandlerDep):
    return await handler.get_pals()


@chat_router.get("/messages/{message_id}")
async def get_message(
    message_id: str,
    token_detail: Annotated[str, Depends(get_token_detail)],
    handler: ChatHandlerDep
):
    """Get a message by its ID"""
    return await handler.get_message(token_detail.user_id, message_id)
