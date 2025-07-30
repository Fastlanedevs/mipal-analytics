from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union
from pydantic import BaseModel, Field
from uuid import UUID

class ChartVisibility(str, Enum):
    """Chart visibility options"""
    PRIVATE = "PRIVATE"  # Only visible to the creator
    ORGANIZATION = "ORGANIZATION"  # Visible to all organization members
    PUBLIC = "PUBLIC"  # Visible to all users


class ChartStatus(str, Enum):
    """Chart processing status"""
    PENDING = "PENDING"      # Task queued, waiting to be processed
    PROCESSING = "PROCESSING" # Currently being generated
    COMPLETED = "COMPLETED"   # Successfully generated
    FAILED = "FAILED"        # Generation failed
    CANCELLED = "CANCELLED"  # User cancelled


class ChartType(str, Enum):
    """Chart type options"""
    # Basic Charts
    BAR = "bar"
    LINE = "line"
    PIE = "pie"
    SCATTER = "scatter"
    AREA = "area"
    
    # Bar Chart Variations
    GROUPED_BAR = "grouped_bar"
    STACKED_BAR = "stacked_bar"
    
    # Line Chart Variations
    MULTI_LINE = "multi_line"
    
    # Pie Chart Variations
    DONUT = "donut"
    
    # Statistical Charts
    BOX_PLOT = "box_plot"
    VIOLIN = "violin"
    HISTOGRAM = "histogram"
    
    # Advanced Charts
    BUBBLE = "bubble"
    RADAR = "radar"
    HEATMAP = "heatmap"
    CANDLESTICK = "candlestick"
    WATERFALL = "waterfall"
    FUNNEL = "funnel"
    SANKEY = "sankey"
    TREE_MAP = "tree_map"
    
    # Special Purpose Charts
    GAUGE = "gauge"
    MAP = "map"
    PARALLEL_COORDINATES = "parallel_coordinates"
    
    EMPTY = ""  # For cases where no chart is applicable


class ChartAdjustmentOption(BaseModel):
    """Options for adjusting an existing chart"""
    chart_type: Optional[ChartType] = None
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    x_offset: Optional[str] = None
    color: Optional[str] = None
    theta: Optional[str] = None


class ChartBase(BaseModel):
    """Base class for chart models"""
    title: str
    description: Optional[str] = None
    chart_type: str
    config: Optional[Dict[str, Any]] = None
    data: Optional[Dict[str, Any]] = None


class Chart(ChartBase):
    """Chart entity model"""
    uid: str
    user_id: str  # ID of the user who created the chart
    org_id: Optional[str] = None  # ID of the organization the chart belongs to
    created_at: datetime
    updated_at: datetime
    chart_schema: Dict[str, Any]  # Schema of the chart data
    chart_data: List[Dict[str, Any]]
    message_id: UUID  # ID of the message this chart is based on
    visibility: ChartVisibility = ChartVisibility.PRIVATE
    last_refreshed_at: datetime
    available_field_mappings: Optional[Dict[str, Any]] = None  # Store available field mappings for chart adjustments
    alternative_visualizations: Optional[List[Dict[str, Any]]] = None  # Store alternative visualizations
    alternative_visualization_queries: Optional[List[Dict[str, Any]]] = None  # Store queries with descriptions for alternative visualizations
    # New fields for async processing
    status: ChartStatus = ChartStatus.COMPLETED
    task_id: Optional[str] = None
    progress: int = 100
    error_message: Optional[str] = None


class ChartTask(BaseModel):
    """Chart generation task entity"""
    task_id: str
    chart_id: Optional[str] = None  # Set when chart is created
    message_id: UUID
    user_id: str
    org_id: Optional[str]
    status: ChartStatus
    progress: int = 0  # 0-100
    error_message: Optional[str] = None
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    
    # Chart generation parameters
    visibility: ChartVisibility
    force_create: bool
    adjustment_query: Optional[str] = None
    
    # Progress tracking
    current_step: str = "queued"  # e.g., "data_extraction", "llm_generation", "schema_creation"
    step_progress: Optional[Dict[str, int]] = {}  # Progress per step

    class Config:
        arbitrary_types_allowed = True
        json_encoders = {
            UUID: str,
            datetime: lambda dt: dt.isoformat() if dt else None
        }


class ChartHistory(ChartBase):
    """Chart history entity model for tracking versions"""
    id: str
    chart_id: str  # ID of the current chart
    chart_data: List[Dict[str, Any]]
    modified_by: str  # ID of the user who made the change
    created_at: datetime


class ChartData(BaseModel):
    """Data container for chart processing"""
    data: List[Dict[str, Any]]
    columns: List[Dict[str, Any]] 