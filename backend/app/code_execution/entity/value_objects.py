from enum import Enum, auto
from typing import Optional, Dict, Any, List
from pydantic import BaseModel, Field


class ExecutionStatus(str, Enum):
    """
    Represents the status of a code execution request.
    """
    QUEUED = "queued"
    PROCESSING = "processing"
    COMPLETED = "completed"
    FAILED = "failed"
    TIMEOUT = "timeout"


class ExecutionResult(BaseModel):
    """
    Represents the result of a code execution.
    Immutable value object that contains execution outputs.
    """
    stdout: str = Field(default="", description="Standard output from the execution")
    stderr: str = Field(default="", description="Standard error from the execution")
    exit_code: int = Field(default=0, description="Exit code from the execution")

    execution_time_ms: Optional[int] = Field(default=None, description="Execution time in milliseconds")
    memory_usage_kb: Optional[int] = Field(default=None, description="Peak memory usage in KB")

    output_files: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of filename to content for any output files"
    )

    class Config:
        frozen = True  # Make this immutable


class ExecutionRequest(BaseModel):
    """
    Represents a request to execute code.
    """
    code: str = Field(..., description="Python code to execute")
    input_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional input data for the execution"
    )
    timeout_seconds: int = Field(
        default=30,
        description="Maximum execution time in seconds"
    )
    
    # Additional fields for more advanced execution requests
    environment_variables: Dict[str, str] = Field(
        default_factory=dict,
        description="Environment variables to set for execution"
    )
    
    memory_limit_mb: Optional[int] = Field(
        default=None,
        description="Memory limit in MB (overrides default)"
    )
    
    allow_network_access: bool = Field(
        default=False,
        description="Whether to allow network access during execution"
    )

    class Config:
        frozen = True


class ResourceLimits(BaseModel):
    """
    Represents resource limits for a container.
    """
    memory_mb: int = Field(default=256, description="Memory limit in MB")
    cpu_limit: float = Field(default=0.25, description="CPU limit (cores)")
    process_limit: int = Field(default=50, description="Maximum number of processes")
    execution_timeout_seconds: int = Field(default=30, description="Execution timeout in seconds")
    network_access: bool = Field(default=False, description="Whether network access is allowed")
    disk_quota_mb: int = Field(default=100, description="Disk space quota in MB")
    max_file_size_kb: int = Field(default=1024, description="Maximum file size in KB")

    class Config:
        frozen = True


class PoolMetrics(BaseModel):
    """
    Metrics about the sandbox pool.
    """
    total_sandboxes: int = Field(description="Total number of sandboxes in the pool")
    available_sandboxes: int = Field(description="Number of available sandboxes")
    busy_sandboxes: int = Field(description="Number of busy sandboxes")
    unhealthy_sandboxes: int = Field(description="Number of unhealthy sandboxes")
    request_queue_length: int = Field(description="Number of requests in the queue")

    average_execution_time_ms: Optional[float] = Field(
        default=None,
        description="Average execution time in milliseconds"
    )
    
    initializing_sandboxes: int = Field(
        default=0,
        description="Number of sandboxes currently initializing"
    )
    
    terminated_sandboxes: int = Field(
        default=0,
        description="Number of sandboxes terminated"
    )
    
    uptime_seconds: Optional[int] = Field(
        default=None,
        description="Pool uptime in seconds"
    )

    class Config:
        frozen = True