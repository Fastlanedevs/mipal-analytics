from typing import Annotated

from fastapi import Depends, Request

from app.auth.api.handlers import AuthHandler


def get_auth_handler(request: Request) -> AuthHandler:
    return request.app.state.container.auth_handler()


# Type aliases for cleaner dependency injection
AuthHandlerDep = Annotated[AuthHandler, Depends(get_auth_handler)]
