# chart_generation.py

from typing import Any, Dict, List, Literal
from pydantic import BaseModel, Field
from app.agents.base_agent import BaseAgent
from app.tokens.service.service import TokensService
from pkg.log.logger import Logger
from pkg.llm_provider.llm_client import LLMModel


# ----------------------------
# Models for Chart Generation
# ----------------------------

class ChartGenerationResults(BaseModel):
    reasoning: str
    chart_type: Literal[
        "line", "multi_line", "bar", "pie", "grouped_bar", "stacked_bar", "area", ""
    ]
    chart_schema: Dict[str, Any]


class ChartGenerationInput(BaseModel):
    query: str = Field(..., description="User's question about data visualization")
    sql: str = Field(..., description="SQL (or Python) code for the analytics result")
    sample_data: List[Dict[str, Any]] = Field(..., description="Sample of the query results")
    columns: List[Dict[str, Any]] = Field(..., description="List of columns (name, type)")


# System Prompt for Generation

chart_generation_system_prompt = """
### TASK ###
You are an expert data analyst and visualization specialist skilled in creating Vega‑Lite charts.
Given the following inputs:
- A user’s question about data visualization,
- The SQL (or Python) code that produced the results,
- A sample of the resulting data,
- A list of columns (each with only the name and type fields),
and the language to use for labels and reasoning, your task is to generate a valid Vega‑Lite chart schema (in JSON) that best represents the data and answers the user’s question.

### OUTPUT FORMAT ###
{
  "reasoning": "<A concise reasoning explaining your chart choice>",
  "chart_type": "<one of: line, multi_line, bar, pie, grouped_bar, stacked_bar, area, or an empty string if no chart is applicable>",
  "chart_schema": { ... }
}
"""


# Chart Generation Agent


class ChartGenerationAgent(Agent[ChartGenerationInput, ChartGenerationResults]):
    def __init__(self, model_name: LLMModel = LLMModel.GEMINI_2_0_FLASH, **kwargs):
        super().__init__(
            system_prompt=chart_generation_system_prompt,
            model=model_name,
            output_type=ChartGenerationResults,
            **kwargs
        )

    async def run(self, input_data: ChartGenerationInput) -> ChartGenerationResults:
        user_message_content = input_data.model_dump_json()
        return await super().run(user_message_content)
