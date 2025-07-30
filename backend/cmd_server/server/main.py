import uvicorn
from fastapi import FastAPI, Request, responses
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from omegaconf import OmegaConf
from starlette.responses import JSONResponse
import os
from starlette.middleware.base import BaseHTTPMiddleware
import asyncio
from typing import Callable, Dict, Any

import app.auth.api.routes as auth_routes
import app.chat.api.routes as chat_routes
import app.integrations.api.routes as integrations_routes
import app.user.api.routes as user_routes
from app.auth.api.routes import auth_router
from app.chat.api.routes import chat_router
from app.integrations.api.routes import integration_router
from app.middleware import AuthMiddleware  # Import the new middleware
from app.user.api.routes import user_router
from cmd_server.server.container import Container, create_container
import app.analytics.api.routes as analytics_routes
from app.analytics.api.routes import analytics_router
from app.tokens.api.routes import tokens_router
import app.tokens.api.routes  as tokens_routes


class TimeoutMiddleware(BaseHTTPMiddleware):
    def __init__(self, app: FastAPI, timeout: int = 300):
        super().__init__(app)
        self.timeout = timeout

    async def dispatch(self, request: Request, call_next: Callable) -> Any:
        try:
            return await asyncio.wait_for(call_next(request), timeout=self.timeout)
        except asyncio.TimeoutError:
            return JSONResponse(
                status_code=504,
                content={"detail": f"Request timeout after {self.timeout} seconds"}
            )

def create_app() -> FastAPI:
    app: FastAPI = FastAPI()

    # Create container once during startup
    container: Container = create_container(cfg=OmegaConf.load("conf/config.yaml"))

    # Store container in app state
    app.state.container = container

    # Add timeout middleware (600 seconds = 10 minutes)
    app.add_middleware(TimeoutMiddleware, timeout=600)

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # In production, replace with specific origins
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["*"],
        max_age=3600,  # Cache preflight requests for 1 hour
    )

    # Add authentication middleware
    app.add_middleware(AuthMiddleware)

    @app.exception_handler(RequestValidationError)
    async def validation_exception_handler(
        request: Request, exc: RequestValidationError
    ):
        def clean_error(error):
            if isinstance(error, bytes):
                return error.decode('utf-8')
            if isinstance(error, dict):
                return {k: clean_error(v) for k, v in error.items()}
            if isinstance(error, list):
                return [clean_error(item) for item in error]
            return str(error)

        errors = [clean_error(err) for err in exc.errors()]
        
        return JSONResponse(
            status_code=422,
            content={"detail": errors},
        )

    @app.exception_handler(Exception)
    async def exception_handler(request: Request, exc: Exception) -> JSONResponse:
        # Clean the error message if it contains bytes
        error_message = str(exc)
        if isinstance(exc, bytes):
            error_message = exc.decode('utf-8')
        
        return JSONResponse(
            status_code=500,
            content={
                "message": "Internal server error",
                "error": error_message
            },
        )

    # Include both routers
    app.include_router(auth_router)
    app.include_router(user_router)
    app.include_router(integration_router)
    app.include_router(chat_router)
    app.include_router(analytics_router)

    app.include_router(tokens_router)

    # Wire the container to both route modules
    container.wire(
        modules=[
            auth_routes,
            user_routes,
            integrations_routes,
            chat_routes,
            analytics_routes,
            tokens_routes,
        ]
    )
    db_initializer = container.db_initializer()

    @app.on_event("startup")
    async def initialize_database():
        """Initialize database schema during application startup"""
        db_initializer = container.db_initializer()
        await db_initializer.initialize_tables()  # Call the async method correctly

    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}



app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, port=8000, timeout_keep_alive=90, timeout_graceful_shutdown=30)
