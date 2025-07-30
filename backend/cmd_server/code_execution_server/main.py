import uvicorn
from fastapi import FastAPI, Request, responses
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from omegaconf import OmegaConf
from starlette.responses import JSONResponse
import os
import sys

from contextlib import asynccontextmanager
from typing import Optional


# Import Routers
from app.code_execution.api.routes import code_execution_router
import app.code_execution.api.routes as code_execution_routes
from app.middleware import AuthMiddleware  # Import the new middleware
from cmd_server.code_execution_server.container import Container, create_container


def create_app() -> FastAPI:
    app: FastAPI = FastAPI()

    # Create container once during startup
    container: Container = create_container(cfg=OmegaConf.load("conf/config.yaml"))

    # Store container in app state
    app.state.container = container


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
    app.include_router(code_execution_router)
    # Wire the container to both route modules
    container.wire(
        modules=[
            code_execution_routes
        ]
    )
    @app.get("/health")
    def health_check() -> dict[str, str]:
        return {"status": "ok"}

    return app


app = create_app()

if __name__ == "__main__":
    uvicorn.run(app, port=8080)
