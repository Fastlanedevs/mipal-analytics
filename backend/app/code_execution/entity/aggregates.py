from datetime import datetime
from typing import Dict, List, Optional, Set, Generator
from pydantic import BaseModel, Field
from uuid import UUID

from .code_execution_entity import CodeExecution
from .value_objects import PoolMetrics


class ExecutionManager(BaseModel):
    """
    Aggregate root for managing CodeExecution entities.
    Tracks active executions and their states.
    """
    active_executions: Dict[UUID, CodeExecution] = Field(
        default_factory=dict,
        description="Currently active code executions"
    )

    sandbox_assignments: Dict[UUID, UUID] = Field(
        default_factory=dict,
        description="Map of execution ID to sandbox ID for active executions"
    )

    class Config:
        validate_assignment = True

    def add_execution(self, execution: CodeExecution) -> None:
        """
        Add an execution to the active executions.
        """
        self.active_executions[execution.id] = execution

    def get_execution(self, execution_id: UUID) -> Optional[CodeExecution]:
        """
        Get an execution by ID.
        """
        return self.active_executions.get(execution_id)

    def assign_sandbox(self, execution_id: UUID, sandbox_id: UUID) -> bool:
        """
        Assign a sandbox to an execution.
        Returns True if successful, False if the execution doesn't exist.
        """
        if execution_id not in self.active_executions:
            return False

        execution = self.active_executions[execution_id]
        execution.mark_as_processing(sandbox_id)
        self.sandbox_assignments[execution_id] = sandbox_id
        return True

    def complete_execution(self, execution_id: UUID) -> Optional[UUID]:
        """
        Mark an execution as completed and return the assigned sandbox ID if any.
        """
        if execution_id not in self.active_executions:
            return None

        # Remove from active executions
        self.active_executions.pop(execution_id)

        # Return sandbox ID if assigned and remove assignment
        if execution_id in self.sandbox_assignments:
            sandbox_id = self.sandbox_assignments.pop(execution_id)
            return sandbox_id

        return None

    def get_assigned_sandbox(self, execution_id: UUID) -> Optional[UUID]:
        """
        Get the sandbox assigned to an execution.
        """
        return self.sandbox_assignments.get(execution_id)
