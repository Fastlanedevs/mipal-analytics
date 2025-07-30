from pydantic import BaseModel, Field, field_validator
from datetime import datetime
from typing import List, Optional, Dict, Any
from enum import Enum
import uuid

class DatabaseType(str, Enum):
    """Enum for database types"""
    POSTGRES = "postgres"
    CSV = "csv"
    EXCEL = "excel"

class Column(BaseModel):
    """Column entity with validation and statistics management"""
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    data_type: str
    description: Optional[str] = None
    is_primary_key: bool = False
    is_nullable: bool = True
    default: Optional[str] = None
    stats: Dict[str, Any] = Field(default_factory=dict)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)

    def update_stats(self, new_stats: Dict[str, Any]) -> None:
        """Update column statistics"""
        self.stats.update(new_stats)
        try:
            self.updated_at = datetime.utcnow()
        except Exception:
            self.updated_at = str(datetime.utcnow())

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Column name cannot be empty")
        return v.strip()

class Table(BaseModel):
    """Table entity with column management and storage info"""
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    schema: str
    description: Optional[str] = None
    columns: List[Column] = Field(default_factory=list)
    row_count: int = 0
    storage_url: Optional[str] = None
    storage_bucket: str = ""
    storage_path: str = ""
    embedding: Optional[List[float]] = None
    is_embedded: bool = False
    last_updated: Optional[datetime] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False

    def add_column(self, column: Column) -> None:
        """Add a new column to the table"""
        if self.is_deleted:
            raise ValueError("Cannot modify a deleted table")
        if any(c.name == column.name for c in self.columns):
            raise ValueError(f"Column {column.name} already exists")
        self.columns.append(column)
        try:
            self.updated_at = datetime.utcnow()
        except Exception:
            self.updated_at = str(datetime.utcnow())

    def update_storage_info(self, bucket: str, path: str, url: Optional[str] = None) -> None:
        """Update storage information"""
        if self.is_deleted:
            raise ValueError("Cannot modify a deleted table")
        self.storage_bucket = bucket
        self.storage_path = path
        self.storage_url = url or f"s3://{bucket}/{path}"
        
        # Use try-except for setting last_updated to prevent potential errors
        try:
            self.last_updated = datetime.utcnow()
        except Exception as e:
            # Fallback to string format if there's any error
            self.last_updated = str(datetime.utcnow())
            
        self.updated_at = datetime.utcnow()

    def update_embedding(self, embedding: List[float]) -> None:
        """Update table embedding for semantic search"""
        if self.is_deleted:
            raise ValueError("Cannot modify a deleted table")
        self.embedding = embedding
        self.is_embedded = True
        try:
            self.updated_at = datetime.utcnow()
        except Exception:
            self.updated_at = str(datetime.utcnow())

    def get_column_by_name(self, name: str) -> Optional[Column]:
        """Get column by name"""
        if self.is_deleted:
            return None
        return next((c for c in self.columns if c.name == name), None)

    def soft_delete(self) -> None:
        """Soft delete the table by marking it as deleted"""
        if self.is_deleted:
            return
        self.is_deleted = True
        try:
            self.deleted_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
        except Exception:
            self.deleted_at = str(datetime.utcnow())
            self.updated_at = str(datetime.utcnow())

    def restore(self) -> None:
        """Restore a soft-deleted table"""
        if not self.is_deleted:
            return
        self.is_deleted = False
        self.deleted_at = None
        try:
            self.updated_at = datetime.utcnow()
        except Exception:
            self.updated_at = str(datetime.utcnow())

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Table name cannot be empty")
        return v.strip()

class Database(BaseModel):
    """Database entity with table management and credentials"""
    uid: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    type: DatabaseType
    description: Optional[str] = None
    tables: List[Table] = Field(default_factory=list)
    user_id: str
    integration_id: str # mapped to Integration integration id
    is_active: bool = True
    credentials: Optional[Dict[str, Any]] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: datetime = Field(default_factory=datetime.utcnow)
    deleted_at: Optional[datetime] = None
    is_deleted: bool = False

    def add_table(self, table: Table) -> None:
        """Add a new table to the database"""
        if self.is_deleted:
            raise ValueError("Cannot modify a deleted database")
        if any(t.name == table.name and not t.is_deleted for t in self.tables):
            raise ValueError(f"Table {table.name} already exists")
        self.tables.append(table)
        try:
            self.updated_at = datetime.utcnow()
        except Exception:
            self.updated_at = str(datetime.utcnow())

    def get_table_by_name(self, name: str, include_deleted: bool = False) -> Optional[Table]:
        """Get table by name"""
        if self.is_deleted and not include_deleted:
            return None
        return next((t for t in self.tables 
                    if t.name == name and (include_deleted or not t.is_deleted)), None)

    def get_table_by_uid(self, uid: str, include_deleted: bool = False) -> Optional[Table]:
        """Get table by UID"""
        if self.is_deleted and not include_deleted:
            return None
        return next((t for t in self.tables 
                    if t.uid == uid and (include_deleted or not t.is_deleted)), None)

    def update_credentials(self, credentials: Dict[str, Any]) -> None:
        """Update database credentials"""
        if self.is_deleted:
            raise ValueError("Cannot modify a deleted database")
        self.credentials = credentials
        try:
            self.updated_at = datetime.utcnow()
        except Exception:
            self.updated_at = str(datetime.utcnow())

    def soft_delete(self) -> None:
        """Soft delete the database and all its tables"""
        if self.is_deleted:
            return
        self.is_deleted = True
        try:
            self.deleted_at = datetime.utcnow()
            self.updated_at = datetime.utcnow()
        except Exception:
            self.deleted_at = str(datetime.utcnow())
            self.updated_at = str(datetime.utcnow())
        # Soft delete all tables
        for table in self.tables:
            if not table.is_deleted:
                table.soft_delete()

    def restore(self, restore_tables: bool = True) -> None:
        """Restore a soft-deleted database and optionally its tables"""
        if not self.is_deleted:
            return
        self.is_deleted = False
        self.deleted_at = None
        try:
            self.updated_at = datetime.utcnow()
        except Exception:
            self.updated_at = str(datetime.utcnow())
        # Restore tables if requested
        if restore_tables:
            for table in self.tables:
                if table.is_deleted:
                    table.restore()

    def get_active_tables(self) -> List[Table]:
        """Get all non-deleted tables"""
        if self.is_deleted:
            return []
        return [t for t in self.tables if not t.is_deleted]

    def get_deleted_tables(self) -> List[Table]:
        """Get all soft-deleted tables"""
        return [t for t in self.tables if t.is_deleted]

    @field_validator('name')
    def validate_name(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("Database name cannot be empty")
        return v.strip()

    @field_validator('user_id')
    def validate_user_id(cls, v: str) -> str:
        if not v.strip():
            raise ValueError("User ID cannot be empty")
        return v.strip() 