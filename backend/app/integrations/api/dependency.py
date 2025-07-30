from typing import Annotated

from fastapi import Depends, Request

from app.integrations.api.handlers import IntegrationHandler


def get_integration_handler(request: Request) -> IntegrationHandler:
    return request.app.state.container.integration_handler()


# Type aliases for cleaner dependency injection
IntegrationHandlerDep = Annotated[IntegrationHandler, Depends(get_integration_handler)]
