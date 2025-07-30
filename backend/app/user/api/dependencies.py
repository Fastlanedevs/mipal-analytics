from typing import Annotated

from fastapi import Depends, Request

from app.user.api.handlers import UserHandler


def get_user_handler(request: Request) -> UserHandler:
    return request.app.state.container.user_handler()


# Type aliases for cleaner dependency injection
UserHandlerDep = Annotated[UserHandler, Depends(get_user_handler)]
