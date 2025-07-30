from sqlalchemy import Column, String, Integer, Text, JSON
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.types import DateTime
from sqlalchemy.sql import func
import uuid

from pkg.db_util.sql_alchemy.declarative_base import Base


class ExecutionResultModel(Base):
    __tablename__ = "execution_results"

    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    execution_id = Column(UUID(as_uuid=True), nullable=False, index=True, unique=True)

    stdout = Column(Text, nullable=False, default="")
    stderr = Column(Text, nullable=False, default="")
    exit_code = Column(Integer, nullable=False, default=0)

    execution_time_ms = Column(Integer, nullable=True)
    memory_usage_kb = Column(Integer, nullable=True)

    output_files = Column(JSON, nullable=True)

    created_at = Column(DateTime, nullable=False, default=func.now())

    def to_entity(self):
        from app.code_execution.entity.value_objects import ExecutionResult

        output_files = self.output_files or {}

        return ExecutionResult(
            stdout=self.stdout,
            stderr=self.stderr,
            exit_code=self.exit_code,
            execution_time_ms=self.execution_time_ms,
            memory_usage_kb=self.memory_usage_kb,
            output_files=output_files
        )

    @staticmethod
    def from_entity(entity, execution_id=None):
        return ExecutionResultModel(
            execution_id=execution_id,
            stdout=entity.stdout,
            stderr=entity.stderr,
            exit_code=entity.exit_code,
            execution_time_ms=entity.execution_time_ms,
            memory_usage_kb=entity.memory_usage_kb,
            output_files=entity.output_files
        )