import json
import logging
from typing import Dict, List, Any, Optional

from app.analytics.errors import ChartCreationError, InvalidChartDataError
from conf.config import AppConfig
from pkg.llm_provider.llm_client import LLMClient, LLMModel

# Import the correct ChartAdjustmentOption class
from app.analytics.agents.chart.chart_adjustment import ChartAdjustmentOption as AgentChartAdjustmentOption
from app.analytics.entity.chart import ChartAdjustmentOption as EntityChartAdjustmentOption
from app.tokens.service.service import TokensService

class ChartGenerationService:
    """Service for generating chart schemas using LLM agents"""

    def __init__(self, tokens_service: TokensService, logger=None, config: Optional[AppConfig] = None, llm_client: Optional[LLMClient] = None,
                 chart_generation_model: LLMModel = LLMModel.GPT_4_1_MINI,
                 chart_adjustment_model: LLMModel = LLMModel.GPT_4_1_MINI
                 ):
        """
        Initialize the chart generation service
        
        Args:
            logger: Optional logger instance
            config: Optional application configuration
            llm_client: Optional LLMClient instance for LLM interactions
        """
        self.logger = logger or logging.getLogger(__name__)
        self.config = config
        self.llm_client = llm_client
        self.chart_generation_model = chart_generation_model
        self.chart_adjustment_model = chart_adjustment_model
        self.tokens_service = tokens_service
        
    def _ensure_valid_vega_lite_schema(self, schema: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ensures the chart schema is a valid Vega-Lite schema by adding required fields if missing.
        
        Args:
            schema: The chart schema to validate
            
        Returns:
            A validated Vega-Lite chart schema
        """
        # Create a copy to avoid modifying the original
        result = schema.copy() if schema else {}
        
        # Ensure $schema field is present
        if '$schema' not in result:
            result['$schema'] = "https://vega.github.io/schema/vega-lite/v5.json"
            
        # Ensure the schema has a mark field
        if 'mark' not in result and 'type' in result:
            # If there's a type field at the root but no mark, use the type as mark
            result['mark'] = result['type']
            
        # Remove 'type' from root level if it exists (should be in 'mark' instead)
        if 'type' in result and result.get('mark'):
            result.pop('type', None)
            
        return result
    
    async def generate_chart_schema(self, 
                                   user_id: str,
                                   data: List[Dict[str, Any]], 
                                   columns: List[Dict[str, Any]],
                                   query: Optional[str] = None,
                                   code: Optional[str] = None,
                                   previous_chart_data: Optional[str] = None,
                                   adjustment_query: Optional[str] = None) -> Dict[str, Any]:
                                   
        """
        Generate a chart schema based on data and columns
        
        Args:
            data: Data to visualize
            columns: Column metadata
            query: Optional user query that generated the data
            code: Optional SQL query or Python code that generated the data
            previous_chart_data: Optional previous chart data to reference when generating a new chart
            adjustment_query: Optional query for requesting an alternate chart visualization
            
        Returns:
            Dictionary containing chart schema and metadata
        """
        self.logger.info("Generating chart schema")
        
        # Import here to avoid circular imports
        from app.analytics.agents.chart.chart_generation import (
            ChartGenerationAgent, 
            ChartGenerationInput,
            ChartGenerationResult
        )
        
        if not data or len(data) == 0:
            raise InvalidChartDataError("No data provided for chart generation")
            
        if not columns or len(columns) == 0:
            raise InvalidChartDataError("No column metadata provided for chart generation")
        
        # Create the generation agent
        agent = ChartGenerationAgent(llm_model=self.chart_generation_model, logger=self.logger, tokens_service=self.tokens_service)
        
        # Prepare input for the agent
        input_data = ChartGenerationInput(
            query=query or "Generate a visualization for this data",
            code=code or "",
            sample_data=data[:500],  # Use first 500 rows as sample
            columns=columns,
            adjustment_query=adjustment_query,
            previous_chart_data=previous_chart_data
        )
        
        try:
            # Run the agent to generate chart schema with retries
            max_retries = 2
            for attempt in range(max_retries):
                try:
                    result = await agent.generate_chart(input_data, user_id=user_id)
                    
                    if not result:
                        raise ChartCreationError("No result returned from agent")
                        
                    # Validate result - ensure it's a ChartGenerationResult
                    if not isinstance(result, ChartGenerationResult):
                        if hasattr(result, 'data') and isinstance(result.data, dict):
                            # If it's a PydanticAI result container, extract and validate the data
                            result_data = result.data
                            
                            # Extract alternative visualizations if available
                            alt_visualizations = result_data.get('alternative_visualizations', [])
                            
                            result = ChartGenerationResult(
                                chart_type=result_data.get('chart_type', 'bar'),
                                reasoning=result_data.get('reasoning', 'Generated chart based on data analysis.'),
                                chart_schema=result_data.get('chart_schema', {}),
                                alternative_visualizations=alt_visualizations
                            )
                        else:
                            raise ChartCreationError(f"Invalid result type: {type(result)}")
                    
                    # Ensure the chart schema is not empty
                    if not result.chart_schema:
                        raise ChartCreationError("Agent returned empty chart schema")
                    
                    # Return the generated schema with validation
                    response = {
                        "chart_type": result.chart_type,
                        "reasoning": result.reasoning,
                        "chart_schema": self._ensure_valid_vega_lite_schema(result.chart_schema)
                    }
                    
                    # Include alternative visualizations if available
                    if hasattr(result, 'alternative_visualizations') and result.alternative_visualizations:
                        self.logger.info(f"Including {len(result.alternative_visualizations)} alternative visualizations")
                        response['alternative_visualizations'] = result.alternative_visualizations
                    
                    # Include alternative visualization queries if available
                    if hasattr(result, 'alternative_visualization_queries') and result.alternative_visualization_queries:
                        self.logger.info(f"Including {len(result.alternative_visualization_queries)} alternative visualization queries")
                        
                        # Convert from pydantic models to dicts if needed
                        alt_queries = []
                        for query_item in result.alternative_visualization_queries:
                            if hasattr(query_item, 'dict'):
                                # If it's a Pydantic model
                                alt_queries.append(query_item.dict())
                            elif isinstance(query_item, dict):
                                # If it's already a dict
                                alt_queries.append(query_item)
                            else:
                                self.logger.warning(f"Skipping unsupported alternative visualization query type: {type(query_item)}")
                        
                        response['alternative_visualization_queries'] = alt_queries
                    
                    return response
                
                except Exception as e:
                    self.logger.warning(f"Chart generation attempt {attempt+1} failed: {str(e)}")
                    if attempt == max_retries - 1:  # Last attempt
                        raise
                    # Otherwise continue to next attempt
            
        except Exception as e:
            self.logger.error(f"Failed to generate chart schema after {max_retries} attempts: {str(e)}")
            raise ChartCreationError(f"Failed to generate chart schema: {str(e)}")
    
    async def adjust_chart(self, 
                         data: List[Dict[str, Any]], 
                         columns: List[Dict[str, Any]],
                         original_schema: Dict[str, Any],
                         adjustment_options: Dict[str, Any],
                         query: Optional[str] = None) -> Dict[str, Any]:
        """
        Adjust an existing chart schema based on adjustment options
        
        Args:
            data: Data to visualize
            columns: Column metadata
            original_schema: Original chart schema
            adjustment_options: Options for adjusting the chart
            query: Optional user query that generated the data
            
        Returns:
            Dictionary containing adjusted chart schema and metadata
        """
        try:
            self.logger.info("Adjusting chart schema")
            
            # Import here to avoid circular imports
            from app.analytics.agents.chart.chart_adjustment import (
                ChartAdjustmentAgent,
                ChartAdjustmentInput,
                ChartAdjustmentOption
            )
            
            if not data or len(data) == 0:
                raise InvalidChartDataError("No data provided for chart adjustment")
                
            if not columns or len(columns) == 0:
                raise InvalidChartDataError("No column metadata provided for chart adjustment")
                
            if not original_schema:
                raise InvalidChartDataError("No original schema provided for chart adjustment")
            
            # Create adjustment option
            if isinstance(adjustment_options, dict):
                # Convert to the agent's ChartAdjustmentOption
                adjustment_option = AgentChartAdjustmentOption(
                    chart_type=adjustment_options.get('chart_type'),
                    x_axis=adjustment_options.get('x_axis'),
                    y_axis=adjustment_options.get('y_axis'),
                    x_offset=adjustment_options.get('x_offset'),
                    color=adjustment_options.get('color'),
                    theta=adjustment_options.get('theta')
                )
            elif isinstance(adjustment_options, EntityChartAdjustmentOption):
                # Convert entity ChartAdjustmentOption to agent ChartAdjustmentOption
                adjustment_option = AgentChartAdjustmentOption(
                    chart_type=str(adjustment_options.chart_type.value) if adjustment_options.chart_type else None,
                    x_axis=adjustment_options.x_axis,
                    y_axis=adjustment_options.y_axis,
                    x_offset=adjustment_options.x_offset,
                    color=adjustment_options.color,
                    theta=adjustment_options.theta
                )
            else:
                # Assume it's already the correct type of ChartAdjustmentOption
                adjustment_option = adjustment_options
            
            # Create the adjustment agent
            agent = ChartAdjustmentAgent(model_name=self.chart_adjustment_model)
            
            # Prepare input for the agent
            input_data = ChartAdjustmentInput(
                query=query or "Adjust visualization for this data",
                sql="",
                sample_data=data[:10],  # Use first 10 rows as sample
                columns=columns,
                original_chart_schema=original_schema,
                adjustment_option=adjustment_option,
                column_metadata=[]  # Optional additional metadata
            )
            
            # Run the agent to adjust chart schema
            result = await agent.run(input_data)
            
            if not result:
                raise ChartCreationError("Failed to adjust chart schema")
                
            if not result.chart_schema:
                # No suitable chart could be generated
                return {
                    "chart_type": "",
                    "reasoning": result.reasoning,
                    "chart_schema": {},
                    "alternative_visualizations": result.alternative_visualizations if hasattr(result, "alternative_visualizations") else None
                }
                
            # Return the adjustment result
            return {
                "chart_type": result.chart_type,
                "reasoning": result.reasoning,
                "chart_schema": result.chart_schema,
                "alternative_visualizations": result.alternative_visualizations if hasattr(result, "alternative_visualizations") else None
            }
            
        except Exception as e:
            self.logger.error(f"Error adjusting chart schema: {str(e)}")
            raise ChartCreationError(f"Failed to adjust chart schema: {str(e)}")
            
    def preprocess_data(self, data: Any) -> List[Dict[str, Any]]:
        """
        Preprocess data to ensure it's in the right format for chart generation
        
        Args:
            data: Data in various formats
            
        Returns:
            Standardized data as list of dictionaries
        """
        try:
            # If data is already a list of dictionaries, return it
            if isinstance(data, list) and all(isinstance(item, dict) for item in data):
                return data
                
            # If data is a string (JSON), parse it
            if isinstance(data, str):
                try:
                    parsed_data = json.loads(data)
                    if isinstance(parsed_data, list) and all(isinstance(item, dict) for item in parsed_data):
                        return parsed_data
                except json.JSONDecodeError:
                    raise InvalidChartDataError("Failed to parse data as JSON")
            
            # If we got here, data format is not supported
            raise InvalidChartDataError("Unsupported data format")
            
        except Exception as e:
            self.logger.error(f"Error preprocessing data: {str(e)}")
            raise InvalidChartDataError(f"Failed to preprocess data: {str(e)}")
    
    def preprocess_columns(self, columns: Any) -> List[Dict[str, Any]]:
        """
        Preprocess columns to ensure they're in the right format
        
        Args:
            columns: Column data in various formats
            
        Returns:
            Standardized column data
        """
        try:
            # If columns is already a list of dictionaries, return it
            if isinstance(columns, list) and all(isinstance(item, dict) for item in columns):
                return columns
                
            # If columns is a string (JSON), parse it
            if isinstance(columns, str):
                try:
                    parsed_columns = json.loads(columns)
                    if isinstance(parsed_columns, list) and all(isinstance(item, dict) for item in parsed_columns):
                        return parsed_columns
                except json.JSONDecodeError:
                    raise InvalidChartDataError("Failed to parse columns as JSON")
            
            # If we got here, columns format is not supported
            raise InvalidChartDataError("Unsupported columns format")
            
        except Exception as e:
            self.logger.error(f"Error preprocessing columns: {str(e)}")
            raise InvalidChartDataError(f"Failed to preprocess columns: {str(e)}") 