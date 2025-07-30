"""
Chart Adjustment Agent for Analytics module.
This agent adjusts existing chart schemas based on specified adjustment options.
"""

import time
import json
from typing import Any, Dict, List, Optional, Union, Literal
from copy import deepcopy

from pydantic import BaseModel, Field
from pydantic_ai.agent import Agent
from pydantic_ai.tools import RunContext

from pkg.llm_provider.llm_client import LLMClient
from pkg.log.logger import Logger

# Import AlternativeVisualization from chart_generation 
from app.analytics.agents.chart.chart_generation import AlternativeVisualization

# Restore the import since these likely have specific VegaLite schema requirements
from app.analytics.agents.chart.prompt.chart_prompts import CHART_ADJUSTMENT_SYSTEM_PROMPT, CHART_ADJUSTMENT_USER_PROMPT

class ChartAdjustmentOption(BaseModel):
    """Options for adjusting a chart."""
    chart_type: Optional[Literal["line", "multi_line", "bar", "pie", "grouped_bar", "stacked_bar", "area", ""]] = Field(None, description="New chart type to use")
    x_axis: Optional[str] = Field(None, description="New x-axis field")
    y_axis: Optional[str] = Field(None, description="New y-axis field")
    x_offset: Optional[str] = Field(None, description="Field to use for x-offset (for grouped charts)")
    color: Optional[str] = Field(None, description="Field to use for color coding")
    theta: Optional[str] = Field(None, description="Field to use for angle in pie/radar charts")

class ChartAdjustmentInput(BaseModel):
    """Input for the ChartAdjustmentAgent."""
    query: str = Field(..., description="The user's query or context for adjustment")
    sql: str = Field("", description="SQL query that generated the data (if available)")
    sample_data: List[Dict[str, Any]] = Field(..., description="Sample of the data for the chart")
    columns: List[Dict[str, Any]] = Field(..., description="Column metadata for the data")
    original_chart_schema: Dict[str, Any] = Field(..., description="Original chart schema to adjust")
    adjustment_option: ChartAdjustmentOption = Field(..., description="Options for adjusting the chart")
    column_metadata: Optional[List[Dict[str, Any]]] = Field([], description="Additional metadata about columns")

class ChartAdjustmentResult(BaseModel):
    """Result from the ChartAdjustmentAgent."""
    chart_type: Literal["line", "multi_line", "bar", "pie", "grouped_bar", "stacked_bar", "area", ""] = Field(..., description="The adjusted chart type")
    reasoning: str = Field(..., description="Explanation of adjustments made")
    chart_schema: Dict[str, Any] = Field(..., description="Complete adjusted chart schema")
    alternative_visualizations: Optional[List[AlternativeVisualization]] = Field(None, description="Alternative visualization options")

class ChartAdjustmentAgent:
    """Agent for adjusting existing chart schemas."""
    
    def __init__(self, model_name: str , logger=None):
        """
        Initialize the Chart Adjustment Agent.
        
        Args:
            model_name: Name of the LLM model to use
            llm_client: LLM client for making API calls
            logger: Logger instance
        """
        self.model_name = model_name
        self.logger = logger or Logger()
        
        self.logger.info(f"ChartAdjustmentAgent.__init__ - Initializing with model: {model_name}")
        
        # Create the pydantic-ai agent with a specific result type
        self._agent = Agent(
            system_prompt=CHART_ADJUSTMENT_SYSTEM_PROMPT,
            model=self.model_name,
            result_type=ChartAdjustmentResult
        )
    
    async def run(self, input_data: ChartAdjustmentInput) -> ChartAdjustmentResult:
        """
        Run the chart adjustment agent directly on the input data.
        
        Args:
            input_data: Input data for chart adjustment
            
        Returns:
            Adjusted chart schema result
        """
        return await self.adjust_chart(input_data)
    
    async def adjust_chart(
        self,
        input_data: ChartAdjustmentInput
    ) -> ChartAdjustmentResult:
        """
        Adjust a chart based on user preferences.
        
        Args:
            input_data: ChartAdjustmentInput containing all necessary data
            
        Returns:
            ChartAdjustmentResult with the adjusted chart schema
        """
        start_time = time.time()
        
        try:
            # Save adjustment option for fallback usage
            self.adjustment_option = input_data.adjustment_option
            
            self.logger.info("=== CHART ADJUSTMENT AGENT INPUT ===")
            self.logger.info(f"Query: {input_data.query}")
            self.logger.info(f"SQL: {input_data.sql}")
            self.logger.info(f"Sample data (first 2 rows): {json.dumps(input_data.sample_data[:2], indent=2)}")
            self.logger.info(f"Columns: {json.dumps(input_data.columns, indent=2)}")
            self.logger.info(f"Original chart schema: {json.dumps(input_data.original_chart_schema, indent=2)}")
            self.logger.info(f"Adjustment options: {json.dumps(input_data.adjustment_option.dict(), indent=2)}")
            self.logger.info("=== END INPUT ===")
            
            try:
                # Format user prompt with input data
                user_prompt = CHART_ADJUSTMENT_USER_PROMPT.format(
                    query=input_data.query,
                    sql=input_data.sql,
                    sample_data=json.dumps(input_data.sample_data, indent=2),
                    columns=json.dumps(input_data.columns, indent=2),
                    original_chart_schema=json.dumps(input_data.original_chart_schema, indent=2),
                    adjustment_option=json.dumps(input_data.adjustment_option.dict(), indent=2)
                )
                
                # Direct approach without RunContext - following pattern from other PAL agents
                result = await self._agent.run(
                    user_prompt,
                    model=self.model_name
                )
                
                # Log the raw result from the agent
                self.logger.info("=== CHART ADJUSTMENT AGENT RAW RESULT ===")
                self.logger.info(f"Result type: {type(result)}")
                
                if hasattr(result, '__dict__'):
                    self.logger.info(f"Result attributes: {dir(result)}")
                    if hasattr(result, 'data'):
                        self.logger.info(f"Result.data: {result.data}")
                else:
                    self.logger.info(f"Result: {result}")
                self.logger.info("=== END RESULT ===")
                
                # Extract the result data from the agent response
                if hasattr(result, 'data') and result.data is not None:
                    chart_result = result.data
                    if isinstance(chart_result, ChartAdjustmentResult):
                        # Log completion
                        duration_ms = (time.time() - start_time) * 1000
                        self.logger.info(f"ChartAdjustmentAgent.adjust_chart - Chart adjustment complete in {duration_ms:.2f}ms")
                        return chart_result
                
                # If we got here and the result is the ChartAdjustmentResult directly
                if isinstance(result, ChartAdjustmentResult):
                    duration_ms = (time.time() - start_time) * 1000
                    self.logger.info(f"ChartAdjustmentAgent.adjust_chart - Chart adjustment complete in {duration_ms:.2f}ms")
                    return result
                
                # If we can't find a valid result, maintain the original schema
                self.logger.warning(f"Could not extract validated result from agent response")
                return self._fallback_result(
                    "Could not extract valid chart schema from agent response", 
                    input_data.original_chart_schema
                )
                
            except Exception as e:
                self.logger.error(f"Error running agent: {str(e)}")
                return self._fallback_result(f"Agent execution error: {str(e)}", 
                                            input_data.original_chart_schema)
                
        except Exception as e:
            self.logger.error(f"ChartAdjustmentAgent.adjust_chart - Error in agent execution: {str(e)}")
            return self._fallback_result(f"Error: {str(e)}")
    
    def _fallback_result(self, error_message: str, original_schema: Optional[Dict[str, Any]] = None) -> ChartAdjustmentResult:
        """
        Create a fallback result when chart adjustment fails.
        
        Args:
            error_message: The error message to log
            original_schema: The original chart schema to maintain
            
        Returns:
            A simple default ChartAdjustmentResult with a Vega-Lite compatible schema
        """
        self.logger.warning(f"Using fallback chart adjustment: {error_message}")
        
        # If we have an original schema, keep that with minimal changes
        if original_schema:
            # Make a deep copy to avoid modifying the original
            schema_with_type = deepcopy(original_schema)
            
            # Try to determine chart type from schema
            chart_type = "bar"  # Default
            if "mark" in schema_with_type:
                mark_value = schema_with_type["mark"]
                if isinstance(mark_value, dict) and "type" in mark_value:
                    mark_type = mark_value["type"]
                    if mark_type in ["line", "bar", "pie", "area"]:
                        chart_type = mark_type
                elif isinstance(mark_value, str) and mark_value in ["line", "bar", "pie", "area"]:
                    chart_type = mark_value
            
            # If user requested pie chart specifically and we have good data, try to create a simple pie
            if hasattr(self, 'adjustment_option') and self.adjustment_option.chart_type == "pie":
                try:
                    # Look for a numeric field for theta
                    numeric_field = None
                    categorical_field = None
                    
                    # Find a numeric field for the theta value
                    if self.adjustment_option.theta:
                        numeric_field = self.adjustment_option.theta
                    else:
                        for column in schema_with_type.get("encoding", {}).values():
                            if isinstance(column, dict) and column.get("type") == "quantitative":
                                numeric_field = column.get("field")
                                break
                    
                    # Find a categorical field for color
                    for column in schema_with_type.get("encoding", {}).values():
                        if isinstance(column, dict) and column.get("type") in ["nominal", "ordinal"]:
                            categorical_field = column.get("field")
                            break
                    
                    if numeric_field and categorical_field:
                        pie_schema = {
                            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
                            "title": schema_with_type.get("title", "Chart"),
                            "width": schema_with_type.get("width", 400),
                            "height": schema_with_type.get("height", 400),
                            "data": schema_with_type.get("data", {"values": []}),
                            "mark": "arc",
                            "encoding": {
                                "theta": {
                                    "field": numeric_field,
                                    "type": "quantitative"
                                },
                                "color": {
                                    "field": categorical_field,
                                    "type": "nominal",
                                    "scale": {"scheme": "category10"}
                                }
                            }
                        }
                        return ChartAdjustmentResult(
                            chart_type="pie",
                            reasoning=f"Fallback: created simple pie chart. The original adjustment failed: {error_message}",
                            chart_schema=pie_schema,
                            alternative_visualizations=[]
                        )
                except Exception as e:
                    self.logger.error(f"Failed to create fallback pie chart: {str(e)}")
                    # Continue to default fallback
            
            # Standard fallback - maintain original schema
            return ChartAdjustmentResult(
                chart_type=chart_type if chart_type in ["line", "multi_line", "bar", "pie", "grouped_bar", "stacked_bar", "area"] else "bar",
                reasoning=f"Fallback: maintained original chart visualization due to adjustment error. {error_message}",
                chart_schema=schema_with_type,
                alternative_visualizations=[]
            )
        
        # If no original schema is available, provide a default empty bar chart
        default_schema = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "Chart Adjustment Error",
            "description": f"Error: {error_message}",
            "data": {"values": []},
            "mark": "bar"
        }
        
        return ChartAdjustmentResult(
            chart_type="bar",
            reasoning=f"Error: Chart adjustment failed. {error_message}",
            chart_schema=default_schema,
            alternative_visualizations=[]
        ) 