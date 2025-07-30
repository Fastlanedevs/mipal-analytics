from typing import Annotated

from fastapi import Depends, Request

from app.chat.api.handlers import ChatHandler


def get_chat_handler(request: Request) -> ChatHandler:
    return request.app.state.container.chat_handler()


# Type aliases for cleaner dependency injection
ChatHandlerDep = Annotated[ChatHandler, Depends(get_chat_handler)]
