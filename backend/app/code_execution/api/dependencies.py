from typing import Annotated

from fastapi import Depends, Request

# Assuming your DI container provides this handler instance
# from app.code_execution.api.handlers import CodeExecutionHandler


def get_code_execution_handler(request: Request) -> 'CodeExecutionHandler':
    """Dependency provider for CodeExecutionHandler"""
    # Replace with your actual container access logic
    # This assumes CodeExecutionHandler is registered in the container
    # accessible via app state.
    try:
        handler = request.app.state.container.code_execution_handler()
        if handler is None:
             raise AttributeError("code_execution_handler not found in container")
        return handler
    except AttributeError as e:
        # Log this error appropriately in a real application
        print(f"Error getting dependency: {e}")
        raise RuntimeError("Dependency injection container not configured correctly for CodeExecutionHandler") from e


# Type Alias for Dependency Injection in routes.py
# Forward reference needed if handlers.py imports this file indirectly
CodeExecutionHandlerDep = Annotated['CodeExecutionHandler', Depends(get_code_execution_handler)]

# Placeholder import to resolve forward reference temporarily if needed,
# ensure CodeExecutionHandler is defined before this is fully resolved.
from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from app.code_execution.api.handlers import CodeExecutionHandler 