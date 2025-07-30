"""
Insight Generator for Analytics PAL.
This agent generates insights from data analysis results.
"""

import time
import json
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from app.agents.base_agent import BaseAgent
from pkg.llm_provider.llm_client import LLMClient, LLMModel
from pkg.log.logger import Logger

from  app.tokens.service.service import TokensService
from app.pal.analytics.utils.agent_logger import AgentLogger
from app.pal.analytics.utils.models import (
    InsightGenerationResult,
    QueryAnalysisResult,
    CodeGenerationResult,
    TableData,
    SchemaInfo,
    VisualizationSuggestion
)
from app.pal.analytics.utils.prompts import INSIGHT_GENERATOR_SYSTEM_PROMPT


class InsightGeneratorInput(BaseModel):
    """Input for the Insight Generator"""
    query: str = Field(..., description="The natural language query")
    query_analysis: Union[Dict[str, Any], QueryAnalysisResult] = Field(..., description="The analysis of the query")
    result_data: str = Field(..., description="The query result data as JSON string")
    schema: Optional[str] = Field(None, description="The database schema information")
    row_count: Optional[int] = Field(None, description="The number of rows in the result")
    column_count: Optional[int] = Field(None, description="The number of columns in the result")


class InsightGenerator:
    """Agent for generating insights from data analysis results"""
    
    def __init__(self, llm_client: LLMClient, tokens_service: TokensService, llm_model: LLMModel, logger:Logger,
                 dev_mode: bool = False):
        """
        Initialize the InsightGenerator agent.
        
        Args:
            llm_client: LLM client for agent communication
            model: Model name to use
            logger: Optional logger instance
            dev_mode: Whether to enable development mode logging
        """
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.logger = logger
        self.tokens_service = tokens_service
        
        self.logger.info(f"InsightGenerator.__init__ - Initializing with model: {self.llm_model}")
        
        # Initialize dev mode logger
        self.dev_logger = AgentLogger(
            enabled=dev_mode,
            agent_name="insight_generator"
        )
        
        # Create the Pydantic AI agent with explicit result type
        self._agent = BaseAgent(
            llm_model=self.llm_model,
            logger=self.logger,
            system_prompt=INSIGHT_GENERATOR_SYSTEM_PROMPT,
            output_type=InsightGenerationResult,
            tokens_service=self.tokens_service
        )
        
    async def run(
        self,
        user_id: str,
        query: str, 
        query_analysis: QueryAnalysisResult, 
        code_result: Any, 
        result_data: Union[Dict[str, Any], List[Dict[str, Any]], TableData, str], 
        schema: Optional[Union[SchemaInfo, str]] = None,
        row_count: Optional[int] = None,
        column_count: Optional[int] = None,
        temperature: float = 0.1
    ) -> InsightGenerationResult:
        """
        Generate insights from query results.
        
        Args:
            query: The original natural language query
            query_analysis: The structured analysis of the query
            code_result: The generated code and result
            result_data: The query result data
            schema: Optional schema information
            row_count: Optional row count for result data
            column_count: Optional column count for result data
            temperature: Temperature parameter for logging (not passed directly to agent.run)
            
        Returns:
            InsightGenerationResult: Generated insights with visualizations
        """
        self.logger.info(f"InsightGenerator.run - Generating insights for: {query}")
        
        try:
            # Format data for insight generation
            formatted_result = self._format_result_data(result_data)
            formatted_schema = self._format_schema_for_insights(schema)
            
            # Get data dimensions if not provided
            if row_count is None or column_count is None:
                detected_row_count, detected_column_count = self._detect_data_dimensions(result_data)
                row_count = row_count or detected_row_count
                column_count = column_count or detected_column_count
            
            # Convert query_analysis to dict if needed
            query_analysis_dict = None
            if isinstance(query_analysis, QueryAnalysisResult):
                try:
                    query_analysis_dict = query_analysis.dict()
                except AttributeError:
                    try:
                        query_analysis_dict = query_analysis.model_dump()
                    except AttributeError:
                        query_analysis_dict = json.loads(query_analysis.json())
            else:
                query_analysis_dict = query_analysis
            
            
            # Add additional context for the LLM
            user_message = f"""
Generate insights and visualization suggestions for the following query and data.

QUERY: {query}

DATA (sample up to 100 rows):
{formatted_result[:10000] + '...' if len(formatted_result) > 10000 else formatted_result}

DATA STATS:
- Rows: {row_count or 'Unknown'}
- Columns: {column_count or 'Unknown'}

Please provide:
1. A summary of key findings
2. Specific insights from the data
"""
            
            # Track timing for development logging
            start_time = time.time()
            
            # Execute the agent with the user message
            try:
                # Note: temperature is handled at the model level in Pydantic AI 0.0.25
                result = await self._agent.run(
                    user_id=user_id,
                    prompt=user_message,
                )
                
                # Extract the typed InsightGenerationResult directly
                insight_result = result.data
                
                # Log for development mode
                if self.dev_logger.enabled:
                    duration_ms = (time.time() - start_time) * 1000
                    self.dev_logger.log_agent_run(
                        input_data={"query": query, "data_dimensions": f"{row_count}x{column_count}"},
                        output=insight_result,
                        llm_client=self.llm_client,
                        temperature=temperature,
                        duration_ms=duration_ms
                    )
                
                self.logger.info(f"InsightGenerator.run - Generated insights with {len(insight_result.insights)} insights.")
                return insight_result
                
            except Exception as e:
                self.logger.error(f"InsightGenerator.run - Error in agent execution: {str(e)}")
                return self._fallback_result(query, error=str(e))
                
        except Exception as e:
            self.logger.error(f"InsightGenerator.run - Unexpected error: {str(e)}")
            return self._fallback_result(query, error=str(e))
            
    def _format_schema_for_insights(self, schema: Optional[Union[SchemaInfo, str]]) -> Optional[str]:
        """
        Format schema for insight generation.
        
        Args:
            schema: Schema information
            
        Returns:
            Formatted schema string or None
        """
        if schema is None:
            return None
            
        if isinstance(schema, str):
            return schema
            
        if isinstance(schema, SchemaInfo):
            # Convert to string representation
            try:
                return schema.json(indent=2)
            except Exception as e:
                self.logger.error(f"Error converting schema to JSON: {str(e)}")
                return None
                
        # Try to serialize as JSON
        try:
            return json.dumps(schema, indent=2)
        except Exception as e:
            self.logger.error(f"Error serializing schema: {str(e)}")
            return None
            
    def _format_result_data(self, result_data: Union[Dict[str, Any], List[Dict[str, Any]], TableData, str]) -> str:
        """
        Format result data for insight generation.
        
        Args:
            result_data: The query result data
            
        Returns:
            Formatted result data as JSON string
        """
        try:
            if isinstance(result_data, str):
                # Already a string, return as is
                return result_data
                
            if isinstance(result_data, TableData):
                # Convert TableData to list of dicts
                rows = result_data.rows
                return json.dumps(rows, default=str)
                
            # Convert to JSON string
            return json.dumps(result_data, default=str)
            
        except Exception as e:
            self.logger.error(f"Error formatting result data: {str(e)}")
            return "[]"
            
    def _detect_data_dimensions(self, result_data: Union[Dict[str, Any], List[Dict[str, Any]], TableData, str]) -> tuple:
        """
        Detect dimensions (row count, column count) of result data.
        
        Args:
            result_data: The query result data
            
        Returns:
            Tuple of (row_count, column_count)
        """
        try:
            if isinstance(result_data, TableData):
                return len(result_data.rows), len(result_data.columns)
                
            if isinstance(result_data, list):
                rows = len(result_data)
                cols = len(result_data[0].keys()) if rows > 0 and isinstance(result_data[0], dict) else 0
                return rows, cols
                
            if isinstance(result_data, dict) and "rows" in result_data and "columns" in result_data:
                return len(result_data["rows"]), len(result_data["columns"])
                
            if isinstance(result_data, str):
                try:
                    # Try to parse as JSON
                    data = json.loads(result_data)
                    if isinstance(data, list):
                        rows = len(data)
                        cols = len(data[0].keys()) if rows > 0 and isinstance(data[0], dict) else 0
                        return rows, cols
                except Exception:
                    pass
                    
            return None, None
            
        except Exception as e:
            self.logger.error(f"Error detecting data dimensions: {str(e)}")
            return None, None
            
    def _fallback_result(self, query: str, error: Optional[str] = None) -> InsightGenerationResult:
        """
        Create a fallback result when insight generation fails.
        
        Args:
            query: The original query
            error: Optional error message
            
        Returns:
            InsightGenerationResult: Basic fallback insights
        """
        error_message = f"Error generating insights: {error}" if error else "Could not generate insights"
        
        self.logger.warning(f"InsightGenerator - Using fallback result: {error_message}")
        
        return InsightGenerationResult(
            summary=f"Could not generate detailed insights for the query: '{query}'. {error_message}",
            insights=[
                {"message": "Insight generation encountered an error", "importance": "high"}
            ],
            visualization_suggestions=[
                VisualizationSuggestion(
                    chart_type="none",
                    title="No visualizations available",
                    description="Could not generate visualization suggestions due to an error"
                )
            ]
        ) 