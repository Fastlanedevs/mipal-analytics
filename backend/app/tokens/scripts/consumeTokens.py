from typing import Optional
import asyncio
from uuid import UUID

from cmd_server.server.container import create_container
from omegaconf import OmegaConf


async def consume_tokens(
    user_id: str, 
    amount: int, 
    description: Optional[str] = "Manual token increase"
) -> None:
    """
    Consume the token count for a specific user.
    
    Args:
        user_id (str): The ID of the user to consume tokens for
        amount (int): The amount of tokens to consume
        description (Optional[str]): Description of why tokens were consumed
        
    Returns:
        None
    """
    # Create container with config
    container = create_container(cfg=OmegaConf.load("conf/config.yaml"))
    
    # Get tokens_service from container
    tokens_service = container.tokens_service()
    
    try:
        # Call refill_tokens method to increase token count
        updated_tokens = await tokens_service.consume_tokens(
            user_id=user_id,
            amount=amount,
            description=description
        )
        
        print(f"Successfully consumed tokens for user {user_id}")
        print(f"New balance: {updated_tokens.current_credits}")
        print(f"Total tokens received: {updated_tokens.total_credits}")
        
    except Exception as e:
        print(f"Error consuming tokens: {str(e)}")


# Example usage
if __name__ == "__main__":
    # Replace with actual user ID
    USER_ID = "d63d687ef15d4941b72c2a1866e371a8"
    TOKEN_AMOUNT = 30000
    
    # Run the async function
    asyncio.run(consume_tokens(USER_ID, TOKEN_AMOUNT, "Development token increase"))