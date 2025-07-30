from pydantic import BaseModel, Field, ConfigDict
from typing import Optional, Dict, Any, List
from uuid import UUID
from datetime import datetime
import pandas as pd
import json


class CodeExecutionRequestDTO(BaseModel):
    """DTO for code execution request"""
    code: str = Field(..., description="Python code to execute")
    input_data: Optional[Dict[str, Any]] = Field(
        default=None,
        description="Optional input data for the execution"
    )
    timeout_seconds: int = Field(
        default=30,
        description="Maximum execution time in seconds"
    )


class CodeExecutionResponseDTO(BaseModel):
    """DTO for basic execution response"""
    execution_id: UUID = Field(..., description="Unique execution ID")
    status: str = Field(..., description="Execution status")
    message: str = Field(..., description="Status message")


class CodeExecutionStatusDTO(BaseModel):
    """DTO for execution status"""
    execution_id: UUID = Field(..., description="Unique execution ID")
    status: str = Field(..., description="Execution status")
    created_at: datetime = Field(..., description="When the execution was created")
    started_at: Optional[datetime] = Field(None, description="When execution started")
    completed_at: Optional[datetime] = Field(None, description="When execution completed")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    result: Optional[Dict[str, Any]] = Field(None, description="Execution result if completed")
    error: Optional[str] = Field(None, description="Error message if failed")


class CodeExecutionResultDTO(BaseModel):
    """DTO for code execution result"""
    model_config = ConfigDict(arbitrary_types_allowed=True)
    
    execution_id: UUID = Field(..., description="Unique execution ID")
    status: str = Field(..., description="Execution status")
    stdout: str = Field(default="", description="Standard output")
    stderr: str = Field(default="", description="Standard error")
    exit_code: int = Field(default=0, description="Exit code")
    execution_time_ms: Optional[int] = Field(None, description="Execution time in milliseconds")
    memory_usage_kb: Optional[int] = Field(None, description="Peak memory usage in KB")
    output_files: Dict[str, str] = Field(
        default_factory=dict,
        description="Map of filename to content for any output files"
    )
    dataframe: Optional[pd.DataFrame] = Field(
        default=None,
        description="DataFrame representation of stdout if it contains tabular data"
    )

    def model_dump(self, **kwargs):
        """Custom model dump to handle DataFrame serialization"""
        data = super().model_dump(**kwargs)
        if isinstance(data.get('dataframe'), pd.DataFrame):
            # Convert DataFrame to JSON-serializable format
            data['dataframe'] = data['dataframe'].to_dict(orient='records')
        return data

    @classmethod
    def model_validate(cls, data):
        """Custom model validation to handle DataFrame deserialization"""
        if isinstance(data, dict) and 'dataframe' in data and isinstance(data['dataframe'], list):
            # Convert list of records back to DataFrame
            data['dataframe'] = pd.DataFrame(data['dataframe'])
        return super().model_validate(data)


class QueueStatusDTO(BaseModel):
    """DTO for queue status"""
    queue_length: int = Field(..., description="Current queue length")
    processing_count: int = Field(..., description="Number of executions being processed")
    average_wait_time_ms: Optional[int] = Field(
        None,
        description="Average wait time in milliseconds"
    )


class ExecutionListDTO(BaseModel):
    """DTO for list of executions"""
    executions: List[CodeExecutionStatusDTO] = Field(
        default_factory=list,
        description="List of executions"
    )
    count: int = Field(..., description="Total number of executions")
