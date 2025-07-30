from datetime import datetime
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field
from uuid import UUID, uuid4

from app.code_execution.entity.value_objects import ExecutionStatus, ExecutionResult


class CodeExecution(BaseModel):
    """
    Represents a single code execution request and its lifecycle.
    This is the main entity for tracking code execution.
    """
    id: UUID = Field(default_factory=uuid4)
    code: str = Field(..., description="Python code to execute")
    status: ExecutionStatus = Field(default=ExecutionStatus.QUEUED)
    input_data: Optional[Dict[str, Any]] = Field(default=None, description="Optional input data for the execution")
    result: Optional[ExecutionResult] = Field(default=None, description="Execution result when completed")
    error_message: Optional[str] = Field(default=None, description="Error message if execution failed")

    sandbox_id: Optional[UUID] = Field(default=None, description="ID of the sandbox used for execution")

    created_at: datetime = Field(default_factory=datetime.utcnow)
    started_at: Optional[datetime] = Field(default=None)
    completed_at: Optional[datetime] = Field(default=None)

    execution_time_ms: Optional[int] = Field(default=None, description="Execution time in milliseconds")
    memory_usage_kb: Optional[int] = Field(default=None, description="Peak memory usage in KB")

    class Config:
        frozen = False  # Allow updates to the entity
        validate_assignment = True  # Validate attributes when they're updated

    def mark_as_processing(self, sandbox_id: UUID) -> None:
        """Mark execution as being processed in a specific sandbox."""
        self.status = ExecutionStatus.PROCESSING
        self.sandbox_id = sandbox_id
        self.started_at = datetime.utcnow()

    def complete(self, result: ExecutionResult, metrics: Dict[str, Any] = None) -> None:
        """Mark execution as completed with results."""
        self.status = ExecutionStatus.COMPLETED
        self.result = result
        self.completed_at = datetime.utcnow()

        if metrics:
            self.execution_time_ms = metrics.get("execution_time_ms")
            self.memory_usage_kb = metrics.get("memory_usage_kb")

    def fail(self, error_message: str) -> None:
        """Mark execution as failed with an error message."""
        self.status = ExecutionStatus.FAILED
        self.error_message = error_message
        self.completed_at = datetime.utcnow()

    def is_finished(self) -> bool:
        """Check if execution is in a terminal state."""
        return self.status in [ExecutionStatus.COMPLETED, ExecutionStatus.FAILED]

    def calculate_execution_time(self) -> Optional[int]:
        """Calculate execution time if started and completed."""
        if self.started_at and self.completed_at:
            delta = self.completed_at - self.started_at
            return int(delta.total_seconds() * 1000)
        return None