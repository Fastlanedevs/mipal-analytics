from typing import Annotated

from fastapi import Depends, Request

from app.tokens.api.handler import TokensHandler
from app.tokens.api.stripe_handler import StripeHandler
from pkg.log.logger import get_logger
import os

def get_tokens_handler(request: Request) -> TokensHandler:
    return request.app.state.container.tokens_handler()

# Type aliases for cleaner dependency injection
TokensHandlerDep = Annotated[TokensHandler, Depends(get_tokens_handler)]

# Create a dependency for StripeHandler that uses the StripeService
def get_stripe_handler(request: Request) -> StripeHandler:
    return request.app.state.container.stripe_handler()

# Annotated dependency for easier use in route functions
StripeHandlerDep = Annotated[StripeHandler, Depends(get_stripe_handler)] 