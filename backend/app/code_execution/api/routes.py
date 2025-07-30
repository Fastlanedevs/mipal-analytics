from fastapi import APIRouter, HTTPException, status, Depends, BackgroundTasks
from typing import Annotated, Optional, Dict, Any
from uuid import UUID
from app.middleware import get_token_detail

from app.code_execution.api.dependencies import CodeExecutionHandlerDep
from app.code_execution.api.dto import (
    CodeExecutionRequestDTO,
    CodeExecutionResponseDTO,
    CodeExecutionResultDTO,
    CodeExecutionStatusDTO,
)

code_execution_router = APIRouter(prefix="/execute", tags=["code-execution"])


@code_execution_router.post("/async", response_model=CodeExecutionResponseDTO)
async def async_execution(
        request: CodeExecutionRequestDTO,
        token_detail: Annotated[dict, Depends(get_token_detail)],
        background_tasks: BackgroundTasks,
        handler: CodeExecutionHandlerDep = None
) -> CodeExecutionResponseDTO:
    """
    Submit code for asynchronous execution.
    Returns execution ID which can be used to check status and retrieve results later.
    """
    execution_id = await handler.submit_execution(
        user_id=token_detail.user_id,
        code=request.code,
        input_data=request.input_data,
        background_tasks=background_tasks
    )

    return CodeExecutionResponseDTO(
        execution_id=execution_id,
        status="queued",
        message="Code execution submitted successfully"
    )


@code_execution_router.post("/sync", response_model=CodeExecutionResultDTO)
async def sync_execution(
        request: CodeExecutionRequestDTO,
        token_detail: Annotated[dict, Depends(get_token_detail)],
        timeout_seconds: int = 30,
        handler: CodeExecutionHandlerDep = None
) -> CodeExecutionResultDTO:
    """
    Execute code synchronously and wait for the result.
    This endpoint will block until execution completes or times out.
    Uses optimized direct execution path that bypasses the queue.
    """
    # Use the optimized direct execution method
    result = await handler.execute_code_sync(
        user_id=token_detail.user_id,
        code=request.code,
        input_data=request.input_data,
        timeout_seconds=timeout_seconds
    )

    return result

@code_execution_router.post("/ml_run", response_model=CodeExecutionResultDTO)
async def ml_run_execution(
        request: CodeExecutionRequestDTO,
        token_detail: Annotated[dict, Depends(get_token_detail)],
        timeout_seconds: int = 30,
        handler: CodeExecutionHandlerDep = None
) -> CodeExecutionResultDTO:
    """
    Execute a machine learning model run synchronously and wait for the result.
    This endpoint will block until execution completes or times out.
    Uses optimized direct execution path that bypasses the queue.
    """
    # Use the optimized direct execution method
    result = await handler.execute_ml_run_sync(
        user_id=token_detail.user_id,
        code=request.code,
        input_data=request.input_data,
        timeout_seconds=timeout_seconds
    )

    return result


@code_execution_router.get("/{execution_id}", response_model=CodeExecutionStatusDTO)
async def get_execution_status(
        execution_id: UUID,
        token_detail: Annotated[dict, Depends(get_token_detail)],
        handler: CodeExecutionHandlerDep = None
) -> CodeExecutionStatusDTO:
    """
    Check the status of an asynchronous code execution.
    Returns status and result if execution is complete.
    """
    return await handler.get_execution_status(
        user_id=token_detail.user_id,
        execution_id=execution_id
    )


@code_execution_router.get("/{execution_id}/result", response_model=CodeExecutionResultDTO)
async def get_execution_result(
        execution_id: UUID,
        token_detail: Annotated[dict, Depends(get_token_detail)],
        handler: CodeExecutionHandlerDep = None
) -> CodeExecutionResultDTO:
    """
    Get the result of a completed code execution.
    Returns 404 if execution not found or not completed.
    """
    result = await handler.get_execution_result(
        user_id=token_detail.user_id,
        execution_id=execution_id
    )

    if not result:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found or not completed"
        )

    return result


@code_execution_router.delete("/{execution_id}", response_model=CodeExecutionResponseDTO)
async def cancel_execution(
        execution_id: UUID,
        token_detail: Annotated[dict, Depends(get_token_detail)],
        handler: CodeExecutionHandlerDep = None
) -> CodeExecutionResponseDTO:
    """
    Cancel a queued or running code execution.
    Returns 404 if execution not found or already completed.
    """
    success = await handler.cancel_execution(
        user_id=token_detail.user_id,
        execution_id=execution_id
    )

    if not success:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Execution not found or already completed"
        )

    return CodeExecutionResponseDTO(
        execution_id=execution_id,
        status="cancelled",
        message="Code execution cancelled successfully"
    )