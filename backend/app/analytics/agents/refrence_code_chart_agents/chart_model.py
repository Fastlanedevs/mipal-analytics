from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel

# Chart Adjustment Option Model
class ChartAdjustmentOption(BaseModel):
    chart_type: Literal["bar", "grouped_bar", "line", "pie", "stacked_bar", "area", "multi_line"]
    x_axis: Optional[str] = None
    y_axis: Optional[str] = None
    x_offset: Optional[str] = None
    color: Optional[str] = None
    theta: Optional[str] = None

# Chart Adjustment Input Model
class ChartAdjustmentInput(BaseModel):
    query: str
    sql: str
    sample_data: List[Dict[str, Any]]
    columns: List[Dict[str, str]]
    original_chart_schema: Dict[str, Any]
    adjustment_option: ChartAdjustmentOption
    column_metadata: List[Dict[str, str]]

# Chart Adjustment Result Model
class ChartAdjustmentResult(BaseModel):
    reasoning: str
    chart_type: Literal["line", "multi_line", "bar", "pie", "grouped_bar", "stacked_bar", "area", ""]
    chart_schema: Dict[str, Any]

# Chart Adjustment Error Model
class ChartAdjustmentError(BaseModel):
    code: Literal["NO_CHART", "OTHERS"]
    message: str

# Chart Adjustment Response Wrapper
class ChartAdjustmentResultResponse(BaseModel):
    status: Literal["understanding", "fetching", "generating", "finished", "failed", "stopped"]
    response: Optional[ChartAdjustmentResult] = None
    error: Optional[ChartAdjustmentError] = None

