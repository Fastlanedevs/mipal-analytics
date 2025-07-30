from typing import Any, Dict, List, Optional, Literal
from pydantic import BaseModel, Field
from app.agents.base_agent import BaseAgent, tool
from chart_generation import ChartGenerationInput, ChartGenerationResults
from chart import chart_generation_instructions
from haystack.components.builders.prompt_builder import PromptBuilder
from chart_model import (
    ChartAdjustmentInput,
    ChartAdjustmentOption,
    ChartAdjustmentResultResponse
)
from pkg.llm_provider.llm_client import LLMModel
from pkg.log.logger import Logger
from app.tokens.service.service import TokensService

# System Prompt for Chart Adjustment

chart_adjustment_system_prompt = f"""
### TASK ###

You are a data analyst great at visualizing data using vega-lite! Given the user's question, SQL, sample data, sample column values, original vega-lite schema and adjustment options, 
you need to re-generate vega-lite schema in JSON and provide suitable chart type.
Besides, you need to give a concise and easy-to-understand reasoning to describe why you provide such vega-lite schema based on the question, SQL, sample data, sample column values, original vega-lite schema and adjustment options.


{chart_generation_instructions}
- If you think the adjustment options are not suitable for the data, you can return an empty string for the schema and chart type and give reasoning to explain why.
### LANGUAGE REQUIREMENT ###
- Always respond in **Query Language** only. Do not use any other language.
### OUTPUT FORMAT ###

Please provide your chain of thought reasoning, chart type and the vega-lite schema in JSON format.

{{
    "reasoning": <REASON_TO_CHOOSE_THE_SCHEMA_IN_STRING_FORMATTED_IN_LANGUAGE_PROVIDED_BY_USER>,
    "chart_type": "line" | "multi_line" | "bar" | "pie" | "grouped_bar" | "stacked_bar" | "area" | "",
    "chart_schema": <VEGA_LITE_JSON_SCHEMA>
}}
"""

chart_adjustment_user_prompt_template = """
### INPUT ###
Original Question: {{ query }}
Original SQL: {{ sql }}
Original Vega-Lite Schema: {{ chart_schema }}
Sample Data: {{ sample_data }}
Sample Column Metadata: {{ column_metadata }}

#### ADJUSTMENT OPTIONS ####
- Requested Chart Type: {{ adjustment_option.chart_type }}
{% if adjustment_option.chart_type != "pie" %}
{% if adjustment_option.x_axis %}
- X Axis: {{ adjustment_option.x_axis }}
{% endif %}
{% if adjustment_option.y_axis %}
- Y Axis: {{ adjustment_option.y_axis }}
{% endif %}
{% endif %}
{% if adjustment_option.x_offset and adjustment_option.chart_type == "grouped_bar" %}
- X Offset: {{ adjustment_option.x_offset }}
{% endif %}
{% if adjustment_option.color and adjustment_option.chart_type != "area" %}
- Color: {{ adjustment_option.color }}
{% endif %}
{% if adjustment_option.theta and adjustment_option.chart_type == "pie" %}
- Theta: {{ adjustment_option.theta }}
{% endif %}

#### IMPORTANT NOTES ####
- The adjustment should be **valid based on the column types**.
- **Reject requests if they violate chart selection rules**.
- **Return an empty schema with reasoning** if no valid chart is possible.

Please think step by step.
"""

# Chart Adjustment Agent # to use user prompt as system prompt we cant use directly so we need to format usinhg haystack

prompt_builder = PromptBuilder(template=chart_adjustment_user_prompt_template)


# Function to generate prompt dynamically

def generate_adjustment_prompt(input_data: ChartAdjustmentInput):
    """Generates a dynamically formatted prompt using Haystack's PromptBuilder."""
    return prompt_builder.run(
        query=input_data.query,
        sql=input_data.sql,
        chart_schema=input_data.original_chart_schema,
        sample_data=input_data.sample_data,
        column_metadata=input_data.column_metadata,
        # Flatten adjustment options (pass individual attributes)
        adjustment_option=input_data.adjustment_option.dict()
    )["prompt"]


# Extract the formatted prompt string

#chart adjustment agent

#  Chart Adjustment Agent with a Tool
class ChartAdjustmentAgent(BaseAgent[ChartAdjustmentInput, ChartAdjustmentResultResponse]):
    def __init__(self, tokens_service: TokensService, logger: Logger, model_name: LLMModel = LLMModel.GEMINI_2_0_FLASH,
                 **kwargs):
        super().__init__(
            system_prompt=chart_adjustment_system_prompt,
            model=model_name,
            logger=logger,
            deps_type=ChartAdjustmentInput,
            result_type=ChartAdjustmentResultResponse,
            tokens_service=tokens_service,
            tools=[self.adjust_chart_schema],  # Register tool
            **kwargs
        )

    #  Define a tool for adjusting the chart schema
    @tool
    async def adjust_chart_schema(ctx: RunContext, input_data: ChartAdjustmentInput) -> Dict[str, Any]:
        """
        Adjusts the Vega-Lite chart schema based on user preferences.
        """
        logger.info(f"📊 Adjusting Chart Schema for {input_data.adjustment_option}")

        # Modify schema based on adjustment options
        adjusted_schema = input_data.original_chart_schema.copy()

        if "data" not in adjusted_schema:
            adjusted_schema["data"] = {"values": input_data.sample_data}

        # Modify chart type
        adjusted_schema["mark"] = input_data.adjustment_option["chart_type"]

        # Modify x-axis, y-axis, color if specified
        encoding = adjusted_schema.get("encoding", {})
        if input_data.adjustment_option.get("x_axis"):
            encoding["x"] = {"field": input_data.adjustment_option["x_axis"], "type": "ordinal"}
        if input_data.adjustment_option.get("y_axis"):
            encoding["y"] = {"field": input_data.adjustment_option["y_axis"], "type": "quantitative"}
        if input_data.adjustment_option.get("color"):
            encoding["color"] = {"field": input_data.adjustment_option["color"], "type": "nominal"}

        adjusted_schema["encoding"] = encoding

        return {
            "reasoning": f"Converted the chart to {input_data.adjustment_option['chart_type']} with new encoding.",
            "chart_type": input_data.adjustment_option["chart_type"],
            "chart_schema": adjusted_schema
        }

    async def run(self, input_data: ChartAdjustmentInput) -> ChartAdjustmentResultResponse:
        """
        Runs the agent and ensures the tool is used.
        """
        user_message_content = input_data.model_dump_json()
        return await super().run(user_message_content)
