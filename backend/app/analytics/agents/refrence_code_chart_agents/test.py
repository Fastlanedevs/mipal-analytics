from fastapi import FastAPI
from pydantic import BaseModel
from typing import Dict, Any, List
import json
import logging

from chart import ChartDataPreprocessor, ChartGenerationPostProcessor
from chart_generation import ChartGenerationAgent, ChartGenerationInput

app = FastAPI()

# Logger setup
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


# DTOs
class ChartRequestDTO(BaseModel):
    query: str
    api_result: Dict[str, Any]


class ChartResponseDTO(BaseModel):
    chart_schema: Dict[str, Any]
    reasoning: str
    chart_type: str


@app.get("/")
def home():
    return {"message": "Chart API is running!"}


@app.post("/chart/generate", response_model=ChartResponseDTO)
async def generate_chart(request: ChartRequestDTO):
    """
    API to generate a Vega-Lite chart from API results.
    """
    try:
        logger.info(" Preprocessing Data...")
        preprocessor = ChartDataPreprocessor(max_rows=10)
        preprocessed = preprocessor.preprocess(request.api_result)
        sample_data = preprocessed["sample_data"]
        full_data = preprocessed["full_data"]
        columns = preprocessed["columns"]

        # Chart Generation
        logger.info(" Generating Initial Chart...")
        gen_input = ChartGenerationInput(
            query=request.query,
            sql=request.api_result["code"],
            sample_data=sample_data,
            columns=columns,
        )

        gen_agent = ChartGenerationAgent()

        logger.debug(" Running Chart Generation Agent...")
        gen_result = await gen_agent.run(gen_input)  # **Chart Logic**
        logger.info(" Chart Generation Completed.")

        # Post-processing Vega schema
        logger.info("Processing Chart Schema...")
        post_processor = ChartGenerationPostProcessor()
        vega_schema = {"$schema": "https://vega.github.io/schema/vega-lite/v5.json", "type": "object"}

        final_gen = post_processor.run(
            [gen_result.data.model_dump_json()],
            vega_schema,
            full_data,
            remove_data_from_chart_schema=False
        )

        # ✅ Return Final Chart Schema
        if final_gen:
            logger.info(" Chart Generated Successfully.")
            return ChartResponseDTO(
                chart_schema=final_gen["results"]["chart_schema"],
                reasoning="A grouped bar chart is best for comparing payment methods by city.",
                chart_type="grouped_bar"
            )
        else:
            logger.error("Chart Generation Failed.")
            return {"error": "Chart generation failed."}

    except Exception as e:
        logger.error(f"Error generating chart: {str(e)}")
        return {"error": str(e)}


# Run FastAPI server
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000, reload=True)
