from fastapi import APIRouter, HTTPException, status, Depends
from typing import Annotated
from app.middleware import get_token_detail
from app.tokens.api.dependencies import TokensHandlerDep
from app.tokens.api.dto import (
    GetUserTokensDTO, 
    GetUserSubscriptionDTO, 
    TokenTransactionListDTO,
)

tokens_router = APIRouter(prefix="", tags=["tokens"])


@tokens_router.get("/credits", response_model=GetUserTokensDTO)
async def get_user_tokens(
    token_detail: Annotated[str, Depends(get_token_detail)],
    handler: TokensHandlerDep = None
) -> GetUserTokensDTO:
    """Get current user's token balance"""
    
    return await handler.get_user_tokens(user_id=token_detail.user_id, email=token_detail.email)


@tokens_router.get("/tokens/subscription", response_model=GetUserSubscriptionDTO)
async def get_user_subscription(
    token_detail: Annotated[str, Depends(get_token_detail)],
    handler: TokensHandlerDep = None,
) -> GetUserSubscriptionDTO:
    """Get current user's subscription details"""

    return await handler.get_user_subscription(user_id=token_detail.user_id, email=token_detail.email)



@tokens_router.get("/tokens/transactions", response_model=TokenTransactionListDTO)
async def get_token_transactions(
    token_detail: Annotated[str, Depends(get_token_detail)],
    limit: int = 50,
    handler: TokensHandlerDep = None
) -> TokenTransactionListDTO:
    """Get token transaction history for the current user"""
    return await handler.get_token_transactions(
        user_id=token_detail.user_id,
        limit=limit
    )
