import uuid
from typing import Dict, List, Optional, Any, Tuple, Protocol
from abc import ABC, abstractmethod
from datetime import datetime

from app.code_execution.entity.code_execution_entity import CodeExecution
from app.code_execution.entity.value_objects import ExecutionStatus, ExecutionResult


# Repository interfaces
class IExecutionRepository(ABC):
    """Interface for the execution repository"""

    @abstractmethod
    async def get_execution(self, execution_id: uuid.UUID) -> Optional[CodeExecution]:
        """Get execution by ID"""
        pass

    @abstractmethod
    async def create_execution(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> CodeExecution:
        """Create a new code execution with QUEUED status"""
        pass

    @abstractmethod
    async def create_execution_with_status(self, code: str, input_data: Optional[Dict[str, Any]] = None,
                                           status: ExecutionStatus = ExecutionStatus.QUEUED) -> CodeExecution:
        """Create a new code execution with specified status"""
        pass

    @abstractmethod
    async def update_execution_status(self, execution_id: uuid.UUID, status: ExecutionStatus) -> Optional[CodeExecution]:
        """Update execution status"""
        pass

    @abstractmethod
    async def complete_execution(self, execution_id: uuid.UUID, result: ExecutionResult,
                                metrics: Optional[Dict[str, Any]] = None) -> Optional[CodeExecution]:
        """Mark execution as completed with results"""
        pass

    @abstractmethod
    async def fail_execution(self, execution_id: uuid.UUID, error_message: str) -> Optional[CodeExecution]:
        """Mark execution as failed with error message"""
        pass

    @abstractmethod
    async def get_executions_by_status(self, status: ExecutionStatus, limit: int = 10) -> List[CodeExecution]:
        """Get executions by status"""
        pass


# Queue interface
class IQueueService(ABC):
    """Interface for managing code execution queue"""

    @abstractmethod
    async def enqueue_execution(self, execution_id: uuid.UUID) -> bool:
        """Add an execution to the queue"""
        pass

    @abstractmethod
    async def dequeue_execution(self) -> Optional[uuid.UUID]:
        """Remove and return the next execution from the queue"""
        pass

    @abstractmethod
    async def complete_processing(self, execution_id: uuid.UUID) -> None:
        """Mark an execution as no longer processing"""
        pass

    @abstractmethod
    async def peek_queue(self, count: int = 10) -> List[Dict[str, Any]]:
        """Peek at the next items in the queue without dequeuing"""
        pass

    @abstractmethod
    async def get_queue_length(self) -> int:
        """Get the current queue length"""
        pass

    @abstractmethod
    async def get_processing_count(self) -> int:
        """Get the number of currently processing executions"""
        pass

    @abstractmethod
    async def get_queue_stats(self) -> Dict[str, Any]:
        """Get statistics about the queue"""
        pass

    @abstractmethod
    async def clear_queue(self) -> int:
        """Clear the queue (for maintenance/testing only)"""
        pass


# Execution service interface
class IExecutionService(ABC):
    """Interface for managing code executions"""

    @abstractmethod
    async def submit_execution(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> CodeExecution:
        """Submit a new code execution request for async processing"""
        pass

    @abstractmethod
    async def execute_code_sync(self, code: str, input_data: Optional[Dict[str, Any]] = None) -> Tuple[
        CodeExecution, bool, Optional[str]]:
        """Execute code synchronously without using the queue"""
        pass
    @abstractmethod
    async def execute_code_local(self, code: str,
                                input_data: Optional[Dict[str, Any]] = None) -> Tuple[CodeExecution, bool, Optional[str]]:
        pass

    @abstractmethod
    async def get_execution(self, execution_id: uuid.UUID) -> Optional[CodeExecution]:
        """Get execution by ID"""
        pass

    @abstractmethod
    async def process_next_execution(self) -> Optional[CodeExecution]:
        """Process the next execution in the queue"""
        pass

    @abstractmethod
    async def execute_code(self, execution_id: uuid.UUID) -> Tuple[bool, Optional[str]]:
        """Execute code for a queued execution"""
        pass

    @abstractmethod
    async def cancel_execution(self, execution_id: uuid.UUID) -> bool:
        """Cancel an execution"""
        pass

    @abstractmethod
    async def get_queued_executions(self, limit: int = 10) -> List[CodeExecution]:
        """Get queued executions"""
        pass

    @abstractmethod
    async def get_processing_executions(self, limit: int = 10) -> List[CodeExecution]:
        """Get processing executions"""
        pass

class ILambdaAdapter(ABC):
    """Interface for executing code via AWS Lambda"""

    @abstractmethod
    async def execute_code(self, code: str, input_data: Optional[Dict[str, Any]] = None,
                           timeout_seconds: int = 30) -> Tuple[ExecutionResult, Dict[str, Any]]:
        """
        Execute code using AWS Lambda
        
        Args:
            code: Python code to execute
            input_data: Optional data to provide to the code
            timeout_seconds: Maximum execution time in seconds
            
        Returns:
            Tuple of (ExecutionResult, metrics)
        """
        pass

    