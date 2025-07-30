"""
Query Analyzer for Analytics PAL.
This agent analyzes natural language queries to determine intent, entities, and more.
"""

import time
import json
from typing import Any, Dict, List, Optional, Union

from pydantic import BaseModel, Field
from pydantic_ai.agent import Agent
from pydantic_ai.tools import RunContext
from pkg.llm_provider.llm_client import LLMClient, LLMModel
from pkg.log.logger import Logger

from app.pal.analytics.utils.models import SchemaInfo, QueryAnalysisResult
from app.pal.analytics.utils.prompts import QUERY_ANALYZER_SYSTEM_PROMPT
from app.pal.analytics.utils.agent_logger import AgentLogger
from app.agents.base_agent import BaseAgent
from app.tokens.service.service import TokensService
from app.tokens.exceptions import TokenLimitError
class QueryAnalyzerInput(BaseModel):
    """Input for the QueryAnalyzer agent."""
    query: str = Field(..., description="The user's natural language query")
    schema: Optional[Union[Dict[str, Any], str]] = Field(None, description="Database schema information")


class QueryAnalyzer:
    """
    Query Analyzer agent for analyzing natural language queries.
    """

    def __init__(self, llm_client: LLMClient, tokens_service: TokensService, llm_model: LLMModel,
                 logger: Logger, dev_mode: bool = False):
        """
        Initialize the QueryAnalyzer agent.
        
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

        self.logger.info(f"QueryAnalyzer.__init__ - Initializing with model: {self.llm_model}")

        # Initialize dev mode logger
        self.dev_logger = AgentLogger(
            enabled=dev_mode,
            agent_name="query_analyzer"
        )

        # Create the Pydantic AI agent - explicitly specifying output_type
        self._agent = BaseAgent(
            llm_model=self.llm_model,
            logger=self.logger,
            system_prompt=QUERY_ANALYZER_SYSTEM_PROMPT,
            output_type=QueryAnalysisResult,
            tokens_service=self.tokens_service,  # Tokens service can be passed if needed
        )

    async def run(
            self,
            user_id: str,
            query: str,
            schema: Optional[Union[SchemaInfo, str]] = None,
            message_history: Optional[List[Dict]] = None,
            temperature: float = 0.1
    ) -> QueryAnalysisResult:
        """
        Analyze a natural language query and extract intent and entities.
        
        Args:
            query: The user's natural language query
            schema: Optional schema information
            temperature: Temperature parameter for LLM
            
        Returns:
            QueryAnalysisResult: Structured analysis of the query
        """
        self.logger.info(f"QueryAnalyzer.run - Analyzing query: {query}")

        try:
            # Determine the database type from schema if available
            db_type = "unknown"
            if isinstance(schema, SchemaInfo):
                db_type = schema.database_type

            # Format schema for query analysis
            formatted_schema = self._format_schema(schema)

            # Track timing for development logging
            start_time = None
            if self.dev_logger.enabled:
                start_time = time.time()

            # Create a user message with the input in JSON format
            user_message = json.dumps({
                "query": query,
                "schema": formatted_schema
            })

            # Execute the agent with input data
            try:
                # Run the agent and get typed result directly
                # Note: temperature is handled at the model level in Pydantic AI 0.0.25
                result = await self._agent.run(
                    user_id=user_id,
                    prompt=user_message,
                    # message_history=message_history
                )


                # Extract the typed QueryAnalysisResult directly from the result data
                query_analysis_result = result.data

                # Log for development mode
                if self.dev_logger.enabled and start_time:
                    duration_ms = (time.time() - start_time) * 1000
                    self.dev_logger.log_agent_run(
                        input_data={"query": query, "schema": formatted_schema},
                        output=query_analysis_result,
                        llm_client=self.llm_client,
                        temperature=temperature,
                        duration_ms=duration_ms
                    )

                self.logger.info(f"QueryAnalyzer.run - Analysis complete. Intent: {query_analysis_result.intent}")
                return query_analysis_result

            except TokenLimitError as e:
                self.logger.error(f"QueryAnalyzer.run - Credits limit exceeded: {str(e)}")
                raise e
            except Exception as e:
                self.logger.error(f"QueryAnalyzer.run - Error in agent execution: {str(e)}")
                raise e

        except TokenLimitError as e:
            self.logger.error(f"QueryAnalyzer.run - Credits limit exceeded: {str(e)}")
            raise e
        except Exception as e:
            self.logger.error(f"QueryAnalyzer.run - Unexpected error: {str(e)}")
            raise e

    def _format_schema(self, schema: Optional[Union[SchemaInfo, str]]) -> Optional[Union[Dict[str, Any], str]]:
        """
        Format schema for query analysis.
        
        Args:
            schema: Schema information
            
        Returns:
            Formatted schema
        """
        if schema is None:
            return None

        if isinstance(schema, str):
            return schema

        if isinstance(schema, SchemaInfo):
            # Convert to dict
            try:
                return schema.dict()
            except AttributeError:
                # Fallback to model_dump for newer Pydantic versions
                try:
                    return schema.model_dump()
                except AttributeError:
                    # Last resort: JSON serialization
                    return json.loads(schema.json())

        # Passed a dict or other JSON-serializable type
        return schema

    def _fallback_result(self, query: str, error: Optional[str] = None) -> QueryAnalysisResult:
        """
        Create a fallback result when analysis fails.
        
        Args:
            query: The original user query
            error: Optional error message
            
        Returns:
            A basic QueryAnalysisResult
        """
        reason = f"Error during query analysis: {error}" if error else "Query could not be analyzed"

        self.logger.warning(f"QueryAnalyzer - Using fallback result: {reason}")

        return QueryAnalysisResult(
            intent="unknown",
            target_entities=[],
            conditions=[],
            complexity="unknown",
            requires_join=False,
            feasible=False,
            reason=reason,
            metrics=[]
        )
