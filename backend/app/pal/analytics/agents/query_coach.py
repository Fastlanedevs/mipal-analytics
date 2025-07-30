"""
Query Coach Agent for analytics.

This agent generates alternative query suggestions when a user's query returns no results.
It helps users refine their queries to get meaningful results from the database.
"""

import json
import asyncio
from typing import List, Dict, Optional, Union, Any
import time

from pydantic import BaseModel, Field
from pydantic_ai.agent import Agent
from pydantic_ai.tools import RunContext
from pkg.llm_provider.llm_client import LLMClient, LLMModel
from pkg.log.logger import Logger
from app.tokens.service.service import TokensService
from app.pal.analytics.utils.agent_logger import AgentLogger
from app.agents.base_agent import BaseAgent


class QuerySuggestion(BaseModel):
    """Data class for representing a query suggestion."""
    title: str = Field(..., description="Brief descriptive title for the suggestion")
    description: str = Field(..., description="Explanation of why this suggestion might work better")
    query: str = Field(..., description="Complete alternative natural language question")


class QueryCoachResult(BaseModel):
    """Result from the Query Coach agent."""
    suggestions: List[QuerySuggestion] = Field(
        ..., 
        description="List of alternative query suggestions"
    )
    explanation: str = Field(
        "", 
        description="Explanation about why the original query returned no results"
    )


class QueryCoachInput(BaseModel):
    """Input for the Query Coach agent."""
    original_query: str = Field(..., description="The original natural language query from the user")
    generated_code: str = Field(..., description="The code generated from the original query")
    code_type: str = Field("sql", description="The type of code generated (sql or python)")
    schema: Optional[Union[Dict[str, Any], str]] = Field(None, description="Database schema information")
    error_message: Optional[str] = Field(None, description="Optional error message from execution")


class QueryCoachAgent:
    """
    Agent that generates alternative query suggestions when a query returns no results.
    
    The QueryCoachAgent helps users by suggesting alternative phrasings or approaches
    when their initial query doesn't return any results.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        tokens_service: TokensService,
        llm_model: LLMModel = LLMModel.GPT_4O_MINI,
        logger=None,
        dev_mode: bool = False
    ):
        """
        Initialize the QueryCoachAgent.
        
        Args:
            llm_client: LLM client for generating suggestions
            model: LLM model to use (either as LLMModel enum or string)
            logger: Optional logger instance
            dev_mode: Whether to enable development mode logging
        """
        self.llm_client = llm_client
        self.logger = logger
        self.agent_name = "query_coach"
        self.llm_model = llm_model
        
        # Initialize dev mode logger
        self.dev_logger = AgentLogger(
            enabled=dev_mode,
            agent_name="query_coach"
        )
        
        # System prompt for the Query Coach agent
        system_prompt = """You are a Query Coach that helps users refine their database queries.

When a user's query returns no results, your job is to suggest alternative queries that might return relevant results.

For each suggestion:
1. Create a clear, concise title (5-7 words)
2. Write a brief explanation of why this alternative might work better
3. Provide the complete natural language question the user should ask

Focus on helping the user get meaningful results by:
- Making the query less restrictive (removing constraints)
- Checking for common mistakes (table/column names, date formats)
- Exploring related questions that might return useful data
- Considering different time periods or broader categories

I will provide you with:
- The original query
- The generated code
- The database schema
- Any error message

You should return 3-5 alternative query suggestions that are more likely to return meaningful results.
"""
        
        # Create the agent with explicit output_type
        self._agent = BaseAgent(
            llm_model=self.llm_model,  # Use the properly formatted model name
            logger=self.logger,
            tokens_service=tokens_service,
            system_prompt=system_prompt,
            output_type=QueryCoachResult,
        )
    
    async def generate_suggestions(
        self,
            user_id: str,
        original_query: str,
        generated_code: str,
        code_type: str = "sql",
        schema: Optional[Union[Dict[str, Any], str]] = None,
        error_message: Optional[str] = None
    ) -> List[QuerySuggestion]:
        """
        Generate alternative query suggestions.
        
        Args:
            original_query: The original natural language query from the user
            generated_code: The code generated from the original query (SQL or Python)
            code_type: The type of code generated (sql or python)
            schema: Optional database schema information
            error_message: Optional error message from execution
            
        Returns:
            List of query suggestions
        """
        self.logger.info(f"QueryCoachAgent.generate_suggestions - Generating suggestions for query: {original_query}")
        
        try:
            # Format the schema for the prompt
            schema_str = self._format_schema(schema)
            
            # Track timing for development logging
            start_time = None
            if self.dev_logger.enabled:
                start_time = time.time()
            
            # Create input for the agent
            input_data = {
                "original_query": original_query,
                "generated_code": generated_code,
                "code_type": code_type,
                "schema": schema_str,
                "error_message": error_message or "The query executed correctly but returned zero rows."
            }
            
            # Run the agent with the prepared input
            result = await self._agent.run(
                user_id=user_id,
                prompt=json.dumps(input_data),
            )
            
            # Extract the suggestions from the result
            coach_result = result.data
            
            # Log for development mode
            if self.dev_logger.enabled and start_time:
                duration_ms = (time.time() - start_time) * 1000
                self.dev_logger.log_agent_run(
                    input_data=input_data,
                    output=coach_result,
                    llm_client=self.llm_client,
                    temperature=0.7,
                    duration_ms=duration_ms
                )
            
            self.logger.info(f"QueryCoachAgent.generate_suggestions - Generated {len(coach_result.suggestions)} suggestions")
            return coach_result.suggestions
            
        except Exception as e:
            self.logger.error(f"QueryCoachAgent.generate_suggestions - Error generating suggestions: {str(e)}")
            
            # Return a fallback suggestion if something went wrong
            return [
                QuerySuggestion(
                    title="Try a broader query",
                    description="Your query might be too specific. Try removing some filters or broadening the scope.",
                    query="Show me all data from this table"
                ),
                QuerySuggestion(
                    title="Check table names",
                    description="Make sure you're using the correct table names in your query.",
                    query=original_query.replace("specific", "general")
                )
            ]
    
    def _format_schema(self, schema) -> str:
        """Format schema information for the prompt."""
        if schema is None:
            return "No schema information available."
            
        if isinstance(schema, str):
            return schema
            
        try:
            # Check if schema has tables attribute (SchemaInfo object)
            if hasattr(schema, 'tables'):
                tables = schema.tables
                formatted = []
                for table in tables:
                    formatted.append(f"Table: {table.name}")
                    for column in table.columns:
                        formatted.append(f"  - {column.name} ({column.data_type})")
                return "\n".join(formatted)
            
            # Handle dictionary format
            if isinstance(schema, dict) and "tables" in schema:
                formatted = []
                for table in schema["tables"]:
                    formatted.append(f"Table: {table['name']}")
                    for column in table.get("columns", []):
                        formatted.append(f"  - {column['name']} ({column.get('data_type', 'unknown')})")
                return "\n".join(formatted)
                
            # As a fallback, just convert to string
            return str(schema)
            
        except Exception as e:
            self.logger.warning(f"Error formatting schema: {str(e)}")
            return str(schema)

    async def run(
        self,
        user_id: str,
        query: str,
        schema: Dict = None,
        error_message: str = None
    ):
        """
        Generate suggestions for improving a failed query.
        
        Args:
            query: The original query that failed
            schema: Database schema information
            error_message: The error message that was returned
            
        Returns:
            QueryCoachResult object containing suggestions
        """
        self.logger.info(f"Generating query suggestions for: {query}")
        
        # Prepare input data
        input_data = {
            "query": query,
            "schema": schema if schema else {},
            "error_message": error_message if error_message else ""
        }
        
        try:
            # Run the agent
            self.logger.info(f"Running QueryCoach agent with model: {self.model_name}")
            agent_result = await self.llm_client.run_agent(
                system_prompt=QUERY_COACH_SYSTEM_PROMPT,
                user_message=QUERY_COACH_USER_PROMPT.format(**input_data),
                llm_model=self.llm_model,  # Use the lowercase, properly formatted model name
                response_format={"type": "json_object"},
                agent_name="query_coach"
            )
            
            # Extract the suggestions from the result
            coach_result = QueryCoachResult(
                suggestions=agent_result.data["suggestions"],
                explanation=agent_result.data["explanation"]
            )
            
            self.logger.info(f"QueryCoachAgent.run - Generated {len(coach_result.suggestions)} suggestions")
            return coach_result
            
        except Exception as e:
            self.logger.error(f"QueryCoachAgent.run - Error generating suggestions: {str(e)}")
            
            # Return a fallback suggestion if something went wrong
            return QueryCoachResult(
                suggestions=[
                    QuerySuggestion(
                        title="Try a broader query",
                        description="Your query might be too specific. Try removing some filters or broadening the scope.",
                        query="Show me all data from this table"
                    ),
                    QuerySuggestion(
                        title="Check table names",
                        description="Make sure you're using the correct table names in your query.",
                        query=query.replace("specific", "general")
                    )
                ],
                explanation="An error occurred while generating suggestions. Please try again later."
            ) 