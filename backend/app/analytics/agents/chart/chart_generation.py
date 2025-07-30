"""
Chart Generation Agent for Analytics module.
This agent analyzes data and generates appropriate chart schemas.
"""

import time
import json
import logging
from typing import Any, Dict, List, Optional, Union, Literal
import requests
from bs4 import BeautifulSoup

from pydantic import BaseModel, Field
from pydantic_ai.agent import Agent
from pydantic_ai.tools import RunContext
from app.analytics.entity.chart import ChartType

from pkg.llm_provider.llm_client import LLMClient, LLMModel
from pkg.log.logger import Logger
from app.agents.base_agent import BaseAgent, tool, system_prompt
from app.tokens.service.service import TokensService
from app.analytics.agents.chart.prompt.chart_prompts import CHART_EXAMPLES

from app.analytics.agents.chart.prompt.chart_prompts import (
    CHART_GENERATION_SYSTEM_PROMPT,
    CHART_GENERATION_USER_PROMPT
)

class ChartGenerationInput(BaseModel):
    """Input for the ChartGenerationAgent."""
    query: str = Field(..., description="The user's query or description of what to visualize")
    code: str = Field("", description="SQL query or Python code that generated the data (if available)")
    sample_data: List[Dict[str, Any]] = Field(..., description="Sample of the data to visualize")
    columns: List[Dict[str, Any]] = Field(..., description="Column metadata for the data")
    adjustment_query: Optional[str] = Field(None, description="Optional query for requesting an alternate chart visualization")
    previous_chart_data: Optional[str] = Field(None, description="Previous chart data to reference when generating a new chart")

class FieldMapping(BaseModel):
    """Field mapping for chart visualizations."""
    x_axis: Optional[str] = Field(None, description="Field for x-axis")
    y_axis: Optional[str] = Field(None, description="Field for y-axis")
    color: Optional[str] = Field(None, description="Field for color encoding")
    theta: Optional[str] = Field(None, description="Field for theta in pie charts")
    column: Optional[str] = Field(None, description="Field for grouping/column")
    tooltip: Optional[List[str]] = Field(None, description="Fields for tooltip")

class AlternativeVisualization(BaseModel):
    """Alternative visualization options."""
    chart_type: Literal["line", "multi_line", "bar", "pie", "grouped_bar", "stacked_bar", "area"] = Field(..., description="Type of chart")
    description: str = Field(..., description="Description of the visualization")
    field_mappings: FieldMapping = Field(..., description="Field mappings for this visualization")

class AlternativeVisualizationQuery(BaseModel):
    """Alternative visualization query with description."""
    query: str = Field(..., description="Natural language query for an alternate visualization")
    description: str = Field(..., description="Explanation of why this alternative might be useful")

class ChartGenerationResult(BaseModel):
    """Result from the ChartGenerationAgent."""
    chart_type: ChartType = Field(..., description="The type of chart to be generated")
    reasoning: str = Field(..., description="Explanation of why this chart type was chosen")
    chart_schema: Dict[str, Any] = Field(..., description="Complete chart schema with all properties")
    alternative_visualization_queries: Optional[List[AlternativeVisualizationQuery]] = Field(None, description="List of alternate visualization queries that can be used to generate different visualizations")


class ChartGenerationAgent(BaseAgent[dict, ChartGenerationResult]):
    """Agent for generating chart schemas from data."""
    
    def __init__(
        self,
        tokens_service: TokensService,
        llm_model: LLMModel,
        logger: Logger,
        retries: int = 2
    ):
        """
        Initialize the Chart Generation Agent.
        
        Args:
            tokens_service: Service for token management
            llm_model: LLM model to use
            logger: Logger instance
            retries: Number of retries for model failures
        """
        super().__init__(
            llm_model=llm_model,
            logger=logger,
            tokens_service=tokens_service,
            instructions=CHART_GENERATION_SYSTEM_PROMPT,
            output_type=ChartGenerationResult,
            retries=2,
            instrument=True
        )
    
    @tool
    async def scrape_vega_lite_docs(self, url:str) -> str:
        """
        Scrape the Vega-Lite documentation from the given URL.

        This tool is used to scrape the Vega-Lite documentation from the given URL.
        It is used to get the Vega-Lite JSON specification for the chart.

        Args:
            url: The URL of the Vega-Lite documentation to scrape

        Returns:
            The Vega-Lite JSON specification for the chart
        """
        try:
            # Validate that the URL is in CHART_EXAMPLES
            valid_urls = [example["url"] for example in CHART_EXAMPLES]
            if url not in valid_urls:
                self.logger.error(f"Invalid URL provided: {url}. URL must be from CHART_EXAMPLES list.")
                return "ERROR: Invalid URL. Only URLs from the CHART_EXAMPLES list are allowed."
            
            self.logger.info(f"****Executing scrape_vega_lite_docs tool with url: {url}****")
            response = requests.get(url)
            soup = BeautifulSoup(response.text, 'html.parser')

            # Look for Vega-Lite spec blocks: often inside <pre> or <code> tags
            code_blocks = soup.find_all(['pre', 'code'])
            
            
            for block in code_blocks:
                text = block.get_text()

                # Check if it looks like a Vega-Lite JSON schema
                if '"$schema"' in text and "vega-lite" in text:
                   
                    return text.strip()[:5000]  # truncate if needed

            return "Vega-Lite JSON specification not found."
        except Exception as e:
            self.logger.error(f"Error in scrape_vega_lite_docs tool: {str(e)}")
            return "Vega-Lite JSON specification not found."
    
    async def generate_chart(self, input_data: ChartGenerationInput, user_id: str) -> ChartGenerationResult:
        """
        Run the chart generation agent.
        """
        try:
            prompt = str(input_data.model_dump())

            run_result = await self.run(prompt=prompt, user_id=user_id)

            self.logger.info(f"****Final Run Result: {run_result.output}****")

            return run_result.output

        except Exception as e:
            self.logger.error(f"Error in chart generation agent: {str(e)}")
            return self._fallback_result(str(e))

    def _fallback_result(self, error_message: str) -> ChartGenerationResult:
        """
        Create a fallback result when chart generation fails.
        
        Args:
            error_message: Error message from the generation attempt
            
        Returns:
            Simple bar chart as a fallback
        """
        self.logger.warning(f"Using fallback chart generation: {error_message}")
        
        # Create a simple bar chart as fallback
        fallback_schema = {
            "$schema": "https://vega.github.io/schema/vega-lite/v5.json",
            "title": "Failed to generate chart",
            "description": f"Error: {error_message}",
            "width": 400,
            "height": 300,
            "data": {"values": []},
            "mark": "bar",
            "encoding": {
                "x": {"field": "category", "type": "nominal"},
                "y": {"field": "value", "type": "quantitative"}
            }
        }
        
        fallback_queries = [
            AlternativeVisualizationQuery(
                query="Show this data as a line chart",
                description="View the data as a trend over time to identify patterns"
            ),
            AlternativeVisualizationQuery(
                query="Create a pie chart to show proportions",
                description="See the relative contribution of each category to the total"
            )
        ]
        
        return ChartGenerationResult(
            chart_type="bar",
            reasoning=f"Fallback chart due to generation error: {error_message}",
            chart_schema=fallback_schema,
            alternative_visualization_queries=fallback_queries
        ) 