from datetime import datetime

from pydantic import BaseModel


class FileResponse(BaseModel):
    id: str


class FileData(BaseModel):
    content: bytes
    filename: str
    file_size: int | None = None
    file_type: str = None
    created_at: datetime = datetime.utcnow()
    updated_at: datetime = datetime.utcnow()
