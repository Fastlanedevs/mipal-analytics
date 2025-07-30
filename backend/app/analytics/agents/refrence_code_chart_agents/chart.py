# chart.py

import logging
from pydantic import BaseModel, Field
from jsonschema import validate, ValidationError
import sys
import orjson
from typing import Any, Dict, List, Literal, Optional



logger = logging.getLogger("chart_generation_agent")
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)




logger = logging.getLogger("chart_generation_agent")
logger.setLevel(logging.INFO)



chart_generation_instructions = """
### INSTRUCTIONS ###

- Chart types: Bar chart, Line chart, Multi line chart, Area chart, Pie chart, Stacked bar chart, Grouped bar chart
- You can only use the chart types provided in the instructions
- Generated chart should answer the user's question and based on the semantics of the SQL query, and the sample data, sample column values are used to help you generate the suitable chart type
- If the sample data is not suitable for visualization, you must return an empty string for the schema and chart type
- If the sample data is empty, you must return an empty string for the schema and chart type
- The language for the chart and reasoning must be the same language provided by the user
- Please use the current time provided by the user to generate the chart
- In order to generate the grouped bar chart, you need to follow the given instructions:
    - Disable Stacking: Add "stack": null to the y-encoding.
    - Use xOffset for subcategories to group bars.
    - Don't use "transform" section.
- In order to generate the pie chart, you need to follow the given instructions:
    - Add {"type": "arc"} to the mark section.
    - Add "theta" encoding to the encoding section.
    - Add "color" encoding to the encoding section.
    - Don't add "innerRadius" to the mark section.
- If the x-axis of the chart is a temporal field, the time unit should be the same as the question user asked.
    - For yearly question, the time unit should be "year".
    - For monthly question, the time unit should be "yearmonth".
    - For weekly question, the time unit should be "yearmonthdate".
    - For daily question, the time unit should be "yearmonthdate".
    - Default time unit is "yearmonth".
- For each axis, generate the corresponding human-readable title based on the language provided by the user.
- Make sure all of the fields(x, y, xOffset, color, etc.) in the encoding section of the chart schema are present in the column names of the data.

### GUIDELINES TO PLOT CHART ###

1. Understanding Your Data Types
- Nominal (Categorical): Names or labels without a specific order (e.g., types of fruits, countries).
- Ordinal: Categorical data with a meaningful order but no fixed intervals (e.g., rankings, satisfaction levels).
- Quantitative: Numerical values representing counts or measurements (e.g., sales figures, temperatures).
- Temporal: Date or time data (e.g., timestamps, dates).
2. Chart Types and When to Use Them
- Bar Chart
    - Use When: Comparing quantities across different categories.
    - Data Requirements:
        - One categorical variable (x-axis).
        - One quantitative variable (y-axis).
    - Example: Comparing sales numbers for different product categories.
- Grouped Bar Chart
    - Use When: Comparing sub-categories within main categories.
    - Data Requirements:
        - Two categorical variables (x-axis grouped by one, color-coded by another).
        - One quantitative variable (y-axis).
        - Example: Sales numbers for different products across various regions.
- Line Chart
    - Use When: Displaying trends over continuous data, especially time.
    - Data Requirements:
        - One temporal or ordinal variable (x-axis).
        - One quantitative variable (y-axis).
    - Example: Tracking monthly revenue over a year.
- Multi Line Chart
    - Use When: Displaying trends over continuous data, especially time.
    - Data Requirements:
        - One temporal or ordinal variable (x-axis).
        - Two or more quantitative variables (y-axis and color).
    - Implementation Notes:
        - Uses `transform` with `fold` to combine multiple metrics into a single series
        - The folded metrics are distinguished using the color encoding
    - Example: Tracking monthly click rate and read rate over a year.
- Area Chart
    - Use When: Similar to line charts but emphasizing the volume of change over time.
    - Data Requirements:
        - Same as Line Chart.
    - Example: Visualizing cumulative rainfall over months.
- Pie Chart
    - Use When: Showing parts of a whole as percentages.
    - Data Requirements:
        - One categorical variable.
        - One quantitative variable representing proportions.
    - Example: Market share distribution among companies.
- Stacked Bar Chart
    - Use When: Showing composition and comparison across categories.
    - Data Requirements: Same as grouped bar chart.
    - Example: Sales by region and product type.
- Guidelines for Selecting Chart Types
    - Comparing Categories:
        - Bar Chart: Best for simple comparisons across categories.
        - Grouped Bar Chart: Use when you have sub-categories.
        - Stacked Bar Chart: Use to show composition within categories.
    - Showing Trends Over Time:
        - Line Chart: Ideal for continuous data over time.
        - Area Chart: Use when you want to emphasize volume or total value over time.
    - Displaying Proportions:
        - Pie Chart: Use for simple compositions at a single point in time.
        - Stacked Bar Chart (100%): Use for comparing compositions across multiple categories.
    
### EXAMPLES ###

1. Bar Chart
- Sample Data:
 [
    {"Region": "North", "Sales": 100},
    {"Region": "South", "Sales": 200},
    {"Region": "East", "Sales": 300},
    {"Region": "West", "Sales": 400}
]
- Chart Schema:
{
    "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>,
    "mark": {"type": "bar"},
    "encoding": {
        "x": {"field": "Region", "type": "nominal", "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>},
        "y": {"field": "Sales", "type": "quantitative", "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>},
        "color": {"field": "Region", "type": "nominal", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}
    }
}
2. Line Chart
- Sample Data:
[
    {"Date": "2022-01-01", "Sales": 100},
    {"Date": "2022-01-02", "Sales": 200},
    {"Date": "2022-01-03", "Sales": 300},
    {"Date": "2022-01-04", "Sales": 400}
]
- Chart Schema:
{
    "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>,
    "mark": {"type": "line"},
    "encoding": {
        "x": {"field": "Date", "type": "temporal", "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>},
        "y": {"field": "Sales", "type": "quantitative", "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>}
    }
}
3. Pie Chart
- Sample Data:
[
    {"Company": "Company A", "Market Share": 0.4},
    {"Company": "Company B", "Market Share": 0.3},
    {"Company": "Company C", "Market Share": 0.2},
    {"Company": "Company D", "Market Share": 0.1}
]
- Chart Schema:
{
    "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>,
    "mark": {"type": "arc"},
    "encoding": {
        "theta": {"field": "Market Share", "type": "quantitative"},
        "color": {"field": "Company", "type": "nominal", "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>}
    }
}
4. Area Chart
- Sample Data:
[
    {"Date": "2022-01-01", "Sales": 100},
    {"Date": "2022-01-02", "Sales": 200},
    {"Date": "2022-01-03", "Sales": 300},
    {"Date": "2022-01-04", "Sales": 400}
]
- Chart Schema:
{
    "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>",
    "mark": {"type": "area"},
    "encoding": {
        "x": {"field": "Date", "type": "temporal", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "y": {"field": "Sales", "type": "quantitative", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}
    }
}
5. Stacked Bar Chart
- Sample Data:
[
    {"Region": "North", "Product": "A", "Sales": 100},
    {"Region": "North", "Product": "B", "Sales": 150},
    {"Region": "South", "Product": "A", "Sales": 200},
    {"Region": "South", "Product": "B", "Sales": 250},
    {"Region": "East", "Product": "A", "Sales": 300},
    {"Region": "East", "Product": "B", "Sales": 350},
    {"Region": "West", "Product": "A", "Sales": 400},
    {"Region": "West", "Product": "B", "Sales": 450}
]
- Chart Schema:
{
    "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>",
    "mark": {"type": "bar"},
    "encoding": {
        "x": {"field": "Region", "type": "nominal", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "y": {"field": "Sales", "type": "quantitative", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>", "stack": "zero"},
        "color": {"field": "Product", "type": "nominal", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}
    }
}
6. Grouped Bar Chart
- Sample Data:
[
    {"Region": "North", "Product": "A", "Sales": 100},
    {"Region": "North", "Product": "B", "Sales": 150},
    {"Region": "South", "Product": "A", "Sales": 200},
    {"Region": "South", "Product": "B", "Sales": 250},
    {"Region": "East", "Product": "A", "Sales": 300},
    {"Region": "East", "Product": "B", "Sales": 350},
    {"Region": "West", "Product": "A", "Sales": 400},
    {"Region": "West", "Product": "B", "Sales": 450}
]
- Chart Schema:
{
    "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>",
    "mark": {"type": "bar"},
    "encoding": {
        "x": {"field": "Region", "type": "nominal", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "y": {"field": "Sales", "type": "quantitative", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "xOffset": {"field": "Product", "type": "nominal", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"},
        "color": {"field": "Product", "type": "nominal", "title": "<TITLE_IN_LANGUAGE_PROVIDED_BY_USER>"}
    }
}
7. Multi Line Chart
- Sample Data:
[
    {"Date": "2022-01-01", "readCount": 100, "clickCount": 10},
    {"Date": "2022-01-02", "readCount": 200, "clickCount": 30},
    {"Date": "2022-01-03", "readCount": 300, "clickCount": 20},
    {"Date": "2022-01-04", "readCount": 400, "clickCount": 40}
]
- Chart Schema:
{
    "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>,
    "mark": {"type": "line"},
    "transform": [
        {
        "fold": ["readCount", "clickCount"],
        "as": ["Metric", "Value"]
        }
    ],
    "encoding": {
        "x": {"field": "Date", "type": "temporal", "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>},
        "y": {"field": "Value", "type": "quantitative", "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>},
        "color": {"field": "Metric", "type": "nominal", "title": <TITLE_IN_LANGUAGE_PROVIDED_BY_USER>}
    }
}
"""

# Chart Schema Definitions

class ChartSchema(BaseModel):
    class ChartType(BaseModel):
        type: Literal["bar", "line", "area", "arc"]

    class ChartEncoding(BaseModel):
        field: str
        type: Literal["ordinal", "quantitative", "nominal"]
        title: str

    title: str
    mark: ChartType
    encoding: ChartEncoding

class TemporalChartEncoding(ChartSchema.ChartEncoding):
    type: Literal["temporal"] = Field(default="temporal")
    timeUnit: str = Field(default="yearmonth")

class LineChartSchema(ChartSchema):
    class LineChartMark(BaseModel):
        type: Literal["line"] = Field(default="line")
    class LineChartEncoding(BaseModel):
        x: TemporalChartEncoding | ChartSchema.ChartEncoding
        y: ChartSchema.ChartEncoding
        color: ChartSchema.ChartEncoding   
    mark: LineChartMark
    encoding: LineChartEncoding

class MultiLineChartSchema(ChartSchema):
    class MultiLineChartMark(BaseModel):
        type: Literal["line"] = Field(default="line")
        
    class MultiLineChartTransform(BaseModel):
        fold: List[str]
        as_: List[str] = Field(alias="as")
        
    class MultiLineChartEncoding(BaseModel):
        x: TemporalChartEncoding | ChartSchema.ChartEncoding
        y: ChartSchema.ChartEncoding
        color: ChartSchema.ChartEncoding
    mark: MultiLineChartMark
    transform: List[MultiLineChartTransform]
    encoding: MultiLineChartEncoding

class BarChartSchema(ChartSchema):
    class BarChartMark(BaseModel):
        type: Literal["bar"] = Field(default="bar")
        
    class BarChartEncoding(BaseModel):
        x: TemporalChartEncoding | ChartSchema.ChartEncoding
        y: ChartSchema.ChartEncoding
        color: ChartSchema.ChartEncoding
    mark: BarChartMark
    encoding: BarChartEncoding

class GroupedBarChartSchema(ChartSchema):
    class GroupedBarChartMark(BaseModel):
        type: Literal["bar"] = Field(default="bar")
        
    class GroupedBarChartEncoding(BaseModel):
        x: TemporalChartEncoding | ChartSchema.ChartEncoding
        y: ChartSchema.ChartEncoding
        xOffset: ChartSchema.ChartEncoding
        color: ChartSchema.ChartEncoding
    mark: GroupedBarChartMark
    encoding: GroupedBarChartEncoding

class StackedBarChartYEncoding(ChartSchema.ChartEncoding):
    stack: Literal["zero"] = Field(default="zero")

class StackedBarChartSchema(ChartSchema):
    class StackedBarChartMark(BaseModel):
        type: Literal["bar"] = Field(default="bar")
        
    class StackedBarChartEncoding(BaseModel):
        x: TemporalChartEncoding | ChartSchema.ChartEncoding
        y: StackedBarChartYEncoding
        color: ChartSchema.ChartEncoding
    mark: StackedBarChartMark
    encoding: StackedBarChartEncoding

class PieChartSchema(ChartSchema):
    class PieChartMark(BaseModel):
        type: Literal["arc"] = Field(default="arc")
        
    class PieChartEncoding(BaseModel):
        theta: ChartSchema.ChartEncoding
        color: ChartSchema.ChartEncoding
    mark: PieChartMark
    encoding: PieChartEncoding

class AreaChartSchema(ChartSchema):
    class AreaChartMark(BaseModel):
        type: Literal["area"] = Field(default="area")
        
    class AreaChartEncoding(BaseModel):
        x: TemporalChartEncoding | ChartSchema.ChartEncoding
        y: ChartSchema.ChartEncoding
    mark: AreaChartMark
    encoding: AreaChartEncoding



# Data Preprocessor

# Data Preprocessor

class ChartDataPreprocessor:
    def __init__(self, max_rows: int = 10):
        self.max_rows = max_rows
        
    def preprocess(self, api_response: Dict) -> Dict:
        if not isinstance(api_response, dict):
          raise TypeError("API response must be a dictionary")
        
        full_results = api_response.get("results", [])
        logger.debug(f"Total results count: {len(full_results)}")

        
        sample_data = full_results[:self.max_rows]
        
        
        logger.info("Created sample of %d rows", len(sample_data))

        
        columns = api_response.get("columns", [])
        
        preprocessed_columns = [{"name": col.get("name"), "type": col.get("type")} for col in columns]
        logger.info("Preprocessed columns: %s", preprocessed_columns)
        
        return {
            "full_data": full_results,
            "sample_data": sample_data,
            "columns": preprocessed_columns
        }

# Chart Generation Post-Processor

class ChartGenerationPostProcessor:
    def run(
        self,
        replies: List[str],
        vega_schema: Dict[str, Any],
        full_data: List[Dict[str, Any]],
        remove_data_from_chart_schema: Optional[bool] = True,  #True: remove full data for LLM; False: inject full data
    ) -> Dict[str, Any]:
        """
        Takes the raw LLM reply, merges in the full dataset if needed,
        validates the final schema, and returns the results.
        """
        try:
            # Deserialize LLM reply
            generation_result = orjson.loads(replies[0])
            if generation_result is None:
                # logger.error("LLM output is null. Returning empty result.")
                return {"results": {"chart_schema": {}, "reasoning": "Error processing reasoning", "chart_type": "Unknown"}}

            reasoning = generation_result.get("reasoning", "No reasoning provided")
            chart_type = generation_result.get("chart_type", "Unknown")
            chart_schema = generation_result.get("chart_schema", {})

            # Ensure chart_schema is a valid dictionary
            if isinstance(chart_schema, str):
                try:
                    chart_schema = orjson.loads(chart_schema)
                except Exception:
                    logger.error(" Failed to parse chart schema as JSON. #Remove this")
                    return {"results": {"chart_schema": {}, "reasoning": "", "chart_type": ""}}

            # Always ensure the Vega‑Lite schema URL is set
            chart_schema["$schema"] = "https://vega.github.io/schema/vega-lite/v5.json"

            # logger.info("Chart Schema BEFORE Processing: %s", chart_schema)

            # Check if the "data" key exists and is a dict
            if "data" not in chart_schema or not isinstance(chart_schema["data"], dict):
                logger.warning("Chart schema missing 'data' field.")
                chart_schema["data"] = {}
                
            if remove_data_from_chart_schema:
                    # For final rendering, restore the full dataset
                chart_schema["data"]["values"] = []
     
            else:                                    # For LLM processing, leave it empty to avoid overload
                chart_schema["data"]["values"] = full_data
              


            # Validate the final schema against the provided Vega‑Lite schema
            validate(chart_schema, schema=vega_schema)
            logger.info("✅ Successfully processed chart schema.")

            return {"results": {"chart_schema": chart_schema, "reasoning": reasoning, "chart_type": chart_type}}
        
        except ValidationError as e:
            logger.error("Vega‑Lite schema is not valid: %s", e)
            return {"results": {"chart_schema": {}, "reasoning": "", "chart_type": ""}}
        except Exception as e:
            logger.error("JSON deserialization failed: %s", e)
            return {"results": {"chart_schema": {}, "reasoning": "", "chart_type": ""}}
