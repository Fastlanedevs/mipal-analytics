from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any
from pydantic import BaseModel, Field

from app.analytics.entity.chart import Chart


class DashboardBase(BaseModel):
    """Base class for dashboard models"""
    title: str
    description: Optional[str] = None
    layout_config: Optional[Dict[str, Any]] = None  # Overall dashboard layout configuration


class Dashboard(DashboardBase):
    """Dashboard entity model"""
    dashboard_id: str
    charts: List[Chart]
    layouts: Any
    user_id: str  # ID of the user who created the dashboard
    org_id: Optional[str] = None  # ID of the organization the dashboard belongs to
    created_at: datetime
    updated_at: datetime
    
