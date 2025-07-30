from typing import List, Optional, Dict, Any, Tuple, Union
import uuid
from uuid import UUID
from datetime import datetime, timezone
import json
import numpy as np
import hashlib
from sqlalchemy import create_engine, select, update, delete, and_, or_, func, text
from sqlalchemy.orm import Session
from sqlalchemy.dialects.postgresql import insert
from pkg.db_util.postgres_conn import PostgresConnection

from app.knowledge_base.service.service import IKnowledgeBaseRepository
from pkg.log.logger import Logger
from sqlalchemy.exc import SQLAlchemyError
import re


def compute_md5hash_id(content: str, prefix: str = "") -> str:
    """Generate a unique MD5 hash ID with optional prefix."""
    return prefix + hashlib.md5(content.encode()).hexdigest()


# ========================================
# CONVERSION FUNCTIONS - COMPLETED
# ========================================


class KnowledgeBaseRepository(IKnowledgeBaseRepository):
    """Repository implementation with LightRAG support"""

    def __init__(self, sql_db_conn: PostgresConnection, logger: Logger):
        self.sql_db_conn = sql_db_conn
        self.logger = logger
        self._indexes_initialized = False