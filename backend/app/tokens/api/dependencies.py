from typing import Annotated

from fastapi import Depends, Request

from app.tokens.api.handler import TokensHandler
from pkg.log.logger import get_logger
import os

def get_tokens_handler(request: Request) -> TokensHandler:
    return request.app.state.container.tokens_handler()

# Type aliases for cleaner dependency injection
TokensHandlerDep = Annotated[TokensHandler, Depends(get_tokens_handler)]
