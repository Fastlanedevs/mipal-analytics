"""
Schema-based Recommendation Generator.

This module provides functionality for generating query recommendations
based on database schema information without requiring a pre-existing query.
"""

import json
import time
from typing import List, Optional, Union, Dict, Any

from pydantic import BaseModel, Field
from pydantic_ai.agent import Agent
from pkg.llm_provider.llm_client import LLMClient
from pkg.log.logger import Logger

from app.pal.analytics.utils.agent_logger import AgentLogger
from app.pal.analytics.utils.models import SchemaInfo
from app.pal.analytics.generators.prompts import RECOMMENDATION_GENERATOR_PROMPT


class RecommendationSuggestion(BaseModel):
    """Data class for representing a query recommendation."""
    title: str = Field(..., description="Brief descriptive title for the recommendation")
    question: str = Field(..., description="Complete natural language question")
    explanation: str = Field(..., description="Explanation of why this query would be useful")
    category: str = Field(..., description="Category of question")


class RecommendationGeneratorResult(BaseModel):
    """Result from the Recommendation Generator agent."""
    recommendations: List[RecommendationSuggestion] = Field(
        ..., 
        description="List of query recommendations"
    )
    

class RecommendationGeneratorInput(BaseModel):
    """Input for the Recommendation Generator agent."""
    schema: Union[Dict[str, Any], str] = Field(..., description="Database schema information")
    database_type: str = Field(..., description="Type of database (postgres, csv, etc.)")
    count: int = Field(5, description="Number of recommendations to generate")


class SchemaBasedRecommendationGenerator:
    """
    Agent that generates query recommendations based on schema information.
    
    This agent analyzes database schema and generates natural language query
    suggestions without requiring a pre-existing query from the user.
    """
    
    def __init__(
        self,
        llm_client: LLMClient,
        model: str = "gpt-4o-mini",
        logger=None,
        dev_mode: bool = False
    ):
        """
        Initialize the SchemaBasedRecommendationGenerator.
        
        Args:
            llm_client: LLM client for generating recommendations
            model: LLM model to use
            logger: Optional logger instance
            dev_mode: Whether to enable development mode logging
        """
        self.llm_client = llm_client
        self.logger = logger or Logger()
        self.agent_name = "schema_recommendation_generator"
        self.model_name = model.lower().replace('_', '-')
        
        # Initialize the agent
        self._agent = Agent(
            model=self.model_name,
            system_prompt=RECOMMENDATION_GENERATOR_PROMPT,
            output_type=RecommendationGeneratorResult
        )
        
        # Initialize dev mode logger if needed
        self.dev_logger = AgentLogger(
            enabled=dev_mode,
            agent_name=self.agent_name
        )

    async def generate_recommendations(
        self,
        schema: Union[Dict[str, Any], str, SchemaInfo],
        database_type: str,
        count: int = 5,
        user_question: Optional[str] = None
    ) -> List[RecommendationSuggestion]:
        """
        Generate query recommendations based on schema information.
        
        Args:
            schema: Database schema information (can be a SchemaInfo object or formatted string)
            database_type: Type of database (postgres, csv, etc.)
            count: Number of recommendations to generate
            
        Returns:
            List of query recommendations
        """
        self.logger.info(f"SchemaBasedRecommendationGenerator.generate_recommendations - Generating {count} recommendations")
        
        try:
            # Track timing for development logging
            start_time = None
            if self.dev_logger.enabled:
                start_time = time.time()
            
            # Create input for the agent
            input_data = {
                "schema": schema,
                "database_type": database_type,
                "count": count,
                "user_question": user_question
            }
            
            # Run the agent with the prepared input
            result = await self._agent.run(
                json.dumps(input_data),
                model=self.model_name
            )
            
            # Extract the recommendations from the result
            recommendations = result.data.recommendations
            
            # Log for development mode
            if self.dev_logger.enabled and start_time:
                duration_ms = (time.time() - start_time) * 1000
                self.dev_logger.log_agent_run(
                    input_data=input_data,
                    output=result.data,
                    llm_client=self.llm_client,
                    temperature=0.7,
                    duration_ms=duration_ms
                )
            
            self.logger.info(f"SchemaBasedRecommendationGenerator.generate_recommendations - Generated {len(recommendations)} recommendations")
            return recommendations
            
        except Exception as e:
            self.logger.error(f"SchemaBasedRecommendationGenerator.generate_recommendations - Error: {str(e)}")
            
            # Return fallback recommendations if something went wrong
            return self._generate_fallback_recommendations(count)
    
    def _format_schema(self, schema):
        """Format schema for use in the prompt"""
        if isinstance(schema, str):
            return schema

        # If it's a dict, convert to JSON string
        return json.dumps(schema, indent=2)
    
    def _generate_fallback_recommendations(self, count: int = 5) -> List[RecommendationSuggestion]:
        """Generate fallback recommendations when an error occurs"""
        fallbacks = [
            RecommendationSuggestion(
                title="Overview of all data",
                explanation="Get a general overview of what's available in the dataset",
                question="Show me a summary of all data",
                category="overview"
            ),
            RecommendationSuggestion(
                title="Top records",
                explanation="See the most important or highest-value records",
                question="What are the top 10 records by value?",
                category="filtering"
            ),
            RecommendationSuggestion(
                title="Recent trends",
                explanation="Understand how the data has changed recently",
                question="Show me trends over the last 30 days",
                category="trend"
            ),
            RecommendationSuggestion(
                title="Key statistics",
                explanation="View basic statistical measures across the dataset",
                question="What are the key statistics for the main metrics?",
                category="aggregation"
            ),
            RecommendationSuggestion(
                title="Data relationships",
                explanation="Explore relationships between different data elements",
                question="How are these data elements related to each other?",
                category="relationship"
            )
        ]
        
        return fallbacks[:count] 