from sqlalchemy import Column, String, Text, JSON, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func
from sqlalchemy import Enum as SQLAlchemyEnum
import uuid

from pkg.db_util.sql_alchemy.declarative_base import Base
from app.code_execution.entity.value_objects import ExecutionStatus


class CodeExecutionModel(Base):
    __tablename__ = "code_executions"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    code = Column(Text, nullable=False)
    status = Column(
        SQLAlchemyEnum(ExecutionStatus, native_enum=False),
        nullable=False,
        default=ExecutionStatus.QUEUED
    )
    input_data = Column(JSON, nullable=True)
    error_message = Column(Text, nullable=True)

    sandbox_id = Column(UUID(as_uuid=True), nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now(), index=True)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)

    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_kb = Column(Integer, nullable=True)

    def to_entity(self):
        from app.code_execution.entity.code_execution_entity import CodeExecution
        from app.code_execution.repository.sql_schema.execution_result import ExecutionResultModel

        # Optional result handling
        result = None
        if self.status == ExecutionStatus.COMPLETED:
            # This would need to be loaded from the execution_results table
            # In a real implementation, this might be done with a join or a separate query
            pass

        return CodeExecution(
            id=self.id,
            code=self.code,
            status=self.status,
            input_data=self.input_data,
            result=result,
            error_message=self.error_message,
            sandbox_id=self.sandbox_id,
            created_at=self.created_at,
            started_at=self.started_at,
            completed_at=self.completed_at,
            execution_time_ms=self.execution_time_ms,
            memory_usage_kb=self.memory_usage_kb
        )

    @staticmethod
    def from_entity(entity):
        return CodeExecutionModel(
            id=entity.id,
            code=entity.code,
            status=entity.status,
            input_data=entity.input_data,
            error_message=entity.error_message,
            sandbox_id=entity.sandbox_id,
            created_at=entity.created_at,
            started_at=entity.started_at,
            completed_at=entity.completed_at,
            execution_time_ms=entity.execution_time_ms,
            memory_usage_kb=entity.memory_usage_kb
        )