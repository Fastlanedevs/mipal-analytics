"""
Data Summarizer Agent

This agent analyzes data and generates a comprehensive summary explaining 
what the data represents, its key characteristics, and important patterns.
"""

import pandas as pd
import json
import time
import traceback
from typing import Dict, Any, Optional, List, Union, AsyncGenerator
from pydantic import BaseModel, Field
from pkg.log.logger import Logger

from pkg.llm_provider.llm_client import LLMClient, LLMModel
from app.agents.base_agent import BaseAgent
from pydantic_ai.messages import (
    PartDeltaEvent,
    TextPartDelta,
    PartStartEvent,
    ToolCallPartDelta
)
from app.pal.analytics.utils.dev_logger import DevLogger
from app.pal.analytics.utils.agent_logger import AgentLogger
from app.tokens.service.service import TokensService


class DataSummarizerInput(BaseModel):
    """Input for the Data Summarizer Agent"""
    data: str = Field(..., description="The data to summarize as a JSON string")
    query: str = Field(..., description="The original user query that generated this data")
    column_info: Optional[List[Dict[str, Any]]] = Field(None, description="Information about the columns in the data")


class DataSummaryResult(BaseModel):
    """Result of data summarization"""
    summary: str = Field(..., description="A comprehensive summary of the data")
    key_points: List[str] = Field(default_factory=list, description="Key points about the data")
    data_shape: Dict[str, Any] = Field(default_factory=dict, description="Information about the data structure")


class DataSummarizer:
    """Agent for generating summaries of data"""

    def __init__(self, llm_client: LLMClient, tokens_service: TokensService, llm_model: LLMModel, logger: Logger,
                 dev_mode: bool = False):
        """
        Initialize the Data Summarizer agent.
        
        Args:
            llm_client: LLM client for generating the analysis
            llm_model: The model to use for generation
            logger: Optional logger
            dev_mode: Whether to enable development mode
        """
        self.llm_client = llm_client
        self.llm_model = llm_model
        self.tokens_service = tokens_service
        self.logger = logger or logging.getLogger(__name__)

        # Set up dev logger for development mode
        self.dev_logger = AgentLogger(
            enabled=dev_mode,
            log_dir="./logs/analytics",
            agent_name="data_summarizer"
        )

        # Create the Pydantic AI agent with explicit result type
        self._agent = BaseAgent(
            llm_model=self.llm_model,
            logger=self.logger,
            tokens_service=self.tokens_service,
            output_type=DataSummaryResult,
            system_prompt=self._get_system_prompt()
        )

        self.logger.info(f"DataSummarizer agent initialized with model: {self.llm_model}")

    async def run(
            self,
            user_id: str,
            data: Union[pd.DataFrame, List[Dict[str, Any]], str],
            query: str,
            column_info: Optional[List[Dict[str, Any]]] = None,
            temperature: float = 0.1
    ) -> DataSummaryResult:
        """
        Generate a comprehensive summary of the data.
        
        Args:
            user_id: The user's ID
            data: The data to summarize (DataFrame, list of dictionaries, or JSON string)
            query: The original user query
            column_info: Optional information about the columns
            temperature: Temperature parameter for LLM (not passed directly to agent.run)
            
        Returns:
            DataSummaryResult: The generated summary
        """
        self.logger.info("DataSummarizer.run - Starting data summarization")
        start_time = time.time()

        try:
            # Convert data to a consistent format
            data_json = self._format_data(data)

            # Prepare the input for the LLM - limit data sample size
            data_sample = data_json[:5000] + '...' if len(data_json) > 5000 else data_json

            # Create a user message with data context
            user_message = f"""
Analyze the following data and provide a comprehensive summary.

USER QUERY: {query}

DATA SAMPLE:
{data_sample}

Please generate a clear summary that explains:
1. What this data represents overall
2. Key characteristics and patterns visible in the data
3. Important insights that can be drawn
4. Potential questions this data could answer
"""

            # Execute the agent with the user message
            try:
                # Note: temperature is handled at the model level in Pydantic AI 0.0.25
                result = await self._agent.run(
                    user_id=user_id,
                    prompt=user_message
                )

                # Extract the typed DataSummaryResult directly
                summary_result = result.data

                # Calculate duration for logging
                duration_ms = (time.time() - start_time) * 1000

                # Log for development mode
                if self.dev_logger.enabled:
                    self.dev_logger.log_agent_run(
                        input_data={"query": query, "data_shape": self._get_data_shape(data)},
                        output=summary_result,
                        llm_client=self.llm_client,
                        temperature=temperature,
                        duration_ms=duration_ms
                    )

                self.logger.info(
                    f"DataSummarizer.run - Generated summary with {len(summary_result.key_points)} key points in {duration_ms:.0f}ms")
                return summary_result

            except Exception as e:
                self.logger.error(f"DataSummarizer.run - Error in agent execution: {str(e)}")
                return self._fallback_result(query, data, error=str(e))

        except Exception as e:
            self.logger.error(f"DataSummarizer.run - Unexpected error: {str(e)}")
            error_traceback = traceback.format_exc()
            self.logger.debug(f"DataSummarizer.run - Error traceback: {error_traceback}")
            return self._fallback_result(query, data, error=str(e))

    async def run_streaming(
            self,
            data: Union[pd.DataFrame, List[Dict[str, Any]], str],
            query: str,
            column_info: Optional[List[Dict[str, Any]]] = None,
            temperature: float = 0.1
    ) -> AsyncGenerator[Dict[str, Any], None]:
        """
        Generate a streaming summary of the data.
        
        Args:
            data: The data to summarize (DataFrame, list of dictionaries, or JSON string)
            query: The original user query
            column_info: Optional information about the columns
            temperature: Temperature parameter for LLM
            
        Yields:
            Dict containing streaming events from the agent execution
        """
        self.logger.info("DataSummarizer.run_streaming - Starting streaming data summarization")
        start_time = time.time()

        try:
            # Convert data to a consistent format
            data_json = self._format_data(data)

            # Prepare the input for the LLM - limit data sample size
            data_sample = data_json[:5000] + '...' if len(data_json) > 5000 else data_json

            # Create a user message with data context
            user_message = f"""
    Analyze the following data and provide a comprehensive summary.

    USER QUERY: {query}

    DATA SAMPLE:
    {data_sample}

    Please generate a clear summary that explains:
    1. What this data represents overall
    2. Key characteristics and patterns visible in the data
    3. Important insights that can be drawn
    4. Potential questions this data could answer

    Break your analysis into clear sections to enable streaming the results to the user gradually.
    """

            # Begin streaming with the agent
            async with self._agent.iter(user_id, user_message) as run:
                async for node in run:
                    if Agent.is_model_request_node(node):
                        # This is where the model is generating content
                        self.logger.info("DataSummarizer.run_streaming - Streaming model generation")

                        async with node.stream(run.ctx) as request_stream:
                            async for event in request_stream:
                                if isinstance(event, PartStartEvent):
                                    self.logger.info(
                                        f"DataSummarizer.run_streaming - Streaming model generation - Starting part {event.index}: {event.part!r}")
                                elif isinstance(event, PartDeltaEvent):
                                    if isinstance(event.delta, TextPartDelta):
                                        # Text is being generated
                                        yield {
                                            "type": "data_summary_delta",
                                            "content": event.delta.content_delta,
                                            "is_final": False
                                        }
                                    elif isinstance(event.delta, ToolCallPartDelta):
                                        # Tool call part delta (in pydantic-ai 0.0.42)
                                        delta_content = event.delta.args_delta

                                        yield {
                                            "type": "data_summary_delta",
                                            "content": delta_content,
                                            "is_final": False
                                        }

                                    else:
                                        # Log unhandled delta types for debugging
                                        self.logger.info(
                                            f"DataSummarizer.run_streaming - Unhandled delta type: {type(event.delta)}")

                    elif Agent.is_end_node(node):
                        # The full result is available
                        self.logger.info(f"DataSummarizer.run_streaming - End node reached, extracting final result")

                        try:
                            summary_result = node.data.data

                            # Log the result structure for debugging
                            self.logger.info(
                                f"DataSummarizer.run_streaming - Final result type: {type(summary_result)}")

                            if hasattr(summary_result, 'summary'):
                                self.logger.info(
                                    f"DataSummarizer.run_streaming - Summary length: {len(summary_result.summary)}")

                            # Yield the final complete result
                            yield {
                                "type": "data_summary_final_result",
                                "content": summary_result.summary,
                                "key_points": summary_result.key_points,
                                "data_shape": summary_result.data_shape,
                                "is_final": True
                            }
                        except Exception as e:
                            self.logger.error(f"DataSummarizer.run_streaming - Error extracting final result: {str(e)}")
                            # Yield error to client
                            yield {
                                "type": "error",
                                "content": f"Error extracting final summary: {str(e)}",
                                "is_final": True
                            }

            # Calculate duration for logging
            duration_ms = (time.time() - start_time) * 1000
            self.logger.info(f"DataSummarizer.run_streaming - Completed streaming in {duration_ms:.0f}ms")

        except Exception as e:
            self.logger.error(f"DataSummarizer.run_streaming - Error: {str(e)}")
            yield {
                "type": "error",
                "content": f"Error generating summary: {str(e)}",
                "is_final": True
            }

    def _format_data(self, data: Union[pd.DataFrame, List[Dict[str, Any]], str]) -> str:
        """
        Format data into a consistent JSON string representation.
        
        Args:
            data: The data to format
            
        Returns:
            Formatted data as a JSON string
        """
        try:
            if isinstance(data, str):
                # Assume it's already JSON
                return data

            if isinstance(data, pd.DataFrame):
                # Convert DataFrame to list of dictionaries
                return json.dumps(data.head(100).to_dict(orient='records'), default=str)

            if isinstance(data, list):
                # Convert list to JSON
                sample = data[:100] if len(data) > 100 else data
                return json.dumps(sample, default=str)

            # Fallback: try to convert to JSON
            return json.dumps(data, default=str)

        except Exception as e:
            self.logger.error(f"DataSummarizer._format_data - Error formatting data: {str(e)}")
            return json.dumps({"error": "Data could not be formatted for analysis"})

    def _get_data_shape(self, data: Union[pd.DataFrame, List[Dict[str, Any]], str]) -> Dict[str, Any]:
        """Get basic shape information about the data"""
        try:
            if isinstance(data, pd.DataFrame):
                return {
                    "rows": len(data),
                    "columns": len(data.columns),
                    "column_names": list(data.columns)
                }
            elif isinstance(data, list):
                return {
                    "rows": len(data),
                    "sample": data[0] if data else {}
                }
            elif isinstance(data, str):
                try:
                    parsed = json.loads(data)
                    if isinstance(parsed, list):
                        return {
                            "rows": len(parsed),
                            "sample": parsed[0] if parsed else {}
                        }
                    return {"data_type": "json_string", "length": len(data)}
                except Exception:
                    return {"data_type": "string", "length": len(data)}

            return {"data_type": str(type(data))}

        except Exception as e:
            self.logger.error(f"Error getting data shape: {str(e)}")
            return {"error": str(e)}

    def _get_system_prompt(self) -> str:
        """Get the system prompt for the agent"""
        return """
You are a data analysis assistant that specializes in summarizing and explaining datasets.

Your task is to create a clear, comprehensive summary of the data provided to you, explaining:
1. What the data represents
2. The key characteristics and patterns
3. Important insights that can be drawn from the data
4. Any limitations or caveats about the data

Use a professional, informative tone. Focus on the most important aspects of the data.
Make sure your summary is well-structured, accurate, and provides genuine value.

Your output should be formatted with a high-level summary followed by specific key points.
"""

    def _fallback_result(self, query: str, data: Any, error: Optional[str] = None) -> DataSummaryResult:
        """Create a fallback result when summarization fails"""
        error_message = f"Error generating summary: {error}" if error else "Could not summarize data"

        self.logger.warning(f"DataSummarizer - Using fallback result: {error_message}")

        # Try to determine data shape for the fallback
        try:
            if isinstance(data, pd.DataFrame):
                shape_info = {"rows": len(data), "columns": len(data.columns)}
            elif isinstance(data, list):
                shape_info = {"rows": len(data)}
            else:
                shape_info = {"type": str(type(data))}
        except Exception:
            shape_info = {"unknown": True}

        return DataSummaryResult(
            summary=f"Unable to generate a detailed summary for this data. {error_message}",
            key_points=["Data summary generation encountered an error"],
            data_shape=shape_info
        )
