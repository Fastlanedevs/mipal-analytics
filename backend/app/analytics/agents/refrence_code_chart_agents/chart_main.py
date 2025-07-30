
# main.py
import asyncio
import sys

from chart import ChartDataPreprocessor, ChartGenerationPostProcessor
from chart_generation import ChartGenerationAgent, ChartGenerationInput
from chart_model import ChartAdjustmentOption
from chart_adjustment import ChartAdjustmentInput, ChartAdjustmentAgent, ChartAdjustmentOption

from pkg.log.logger import Logger
from pkg.tokens.service.service import TokensService

import json  




async def main():
    # Simulated API response (this is the output from your analysis API)

    logger = Logger()
    
    logger.info("=======starting chart proces==========")
    api_result = {
    "code": "WITH category_sales AS (\nSELECT\np.\"product_category_name\",\nSUM(oi.\"price\") AS \"total_sales\"\nFROM\n\"public\".\"order_items\" oi\nJOIN\n\"public\".\"products\" p ON oi.\"product_id\" = p.\"product_id\"\nGROUP BY\np.\"product_category_name\"\n), total_sales AS (\nSELECT SUM(\"total_sales\") AS \"grand_total\" FROM category_sales\n)\nSELECT\nc.\"product_category_name\",\nc.\"total_sales\",\nROUND((c.\"total_sales\" / t.\"grand_total\") * 100, 2) AS \"sales_percentage\"\nFROM category_sales c, total_sales t\nORDER BY c.\"total_sales\" DESC\nLIMIT 5;",
    "code_type": "sql",
    "explanation": "This SQL query retrieves the top 5 product categories based on total sales and calculates their percentage contribution to the total sales.",
    "results": [
        {
            "product_category_name": "electronics",
            "total_sales": 500000,
            "sales_percentage": 35.7
        },
        {
            "product_category_name": "furniture",
            "total_sales": 300000,
            "sales_percentage": 21.4
        },
        {
            "product_category_name": "clothing",
            "total_sales": 200000,
            "sales_percentage": 14.3
        },
        {
            "product_category_name": "sports",
            "total_sales": 150000,
            "sales_percentage": 10.7
        },
        {
            "product_category_name": "books",
            "total_sales": 100000,
            "sales_percentage": 7.1
        }
    ],
    "error": None,
    "columns": [
        {
            "name": "product_category_name",
            "display_name": "Product Category Name",
            "type": "VARCHAR",
            "align": "left",
            "sortable": True,
            "filterable": True,
            "hidden": False,
            "description": "Name of the product category"
        },
        {
            "name": "total_sales",
            "display_name": "Total Sales",
            "type": "FLOAT",
            "align": "right",
            "sortable": True,
            "filterable": True,
            "hidden": False,
            "description": "Total sales revenue for the category"
        },
        {
            "name": "sales_percentage",
            "display_name": "Sales Percentage",
            "type": "FLOAT",
            "align": "right",
            "sortable": True,
            "filterable": True,
            "hidden": False,
            "description": "Percentage contribution of category to total sales"
        }
    ],
    "summary": {
        "total_rows": 5,
        "total_columns": 3,
        "insights": [
            "Electronics contribute the most to total sales, making up 35.7% of all sales.",
            "Books have the smallest share, contributing only 7.1%."
        ],
        "overview": "This dataset contains sales data for the top 5 product categories, showing their total revenue and contribution to total sales.",
        "numeric_insights": [
            "Total sales revenue ranges from 100,000 (books) to 500,000 (electronics)."
        ],
        "categorical_insights": [
            "Categories like electronics and furniture dominate the sales distribution."
        ]
    }
}



        # Preprocess API response
    logger.info(" Preprocessing Data...")
    preprocessor = ChartDataPreprocessor(max_rows=10)
    preprocessed = preprocessor.preprocess(api_result)
    sample_data = preprocessed["sample_data"]
    full_data = preprocessed["full_data"]
    columns = preprocessed["columns"]

        # Chart Generation
    logger.info(" Generating Initial Chart...")
    gen_input = ChartGenerationInput(
            query="What is the percentage contribution of the top 5 product categories to total sales?",
            sql=api_result["code"],
            sample_data=sample_data,
            columns=columns,
        )

    gen_agent = ChartGenerationAgent()

    logger.debug(" Running Chart Generation Agent...")
    gen_result = await gen_agent.run(gen_input)  # **Potential Error Here**
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

        #  Logging Final Chart Schema
    if final_gen:
     logger.info("=== Final Chart Output ===")
     logger.info("Reasoning: %s", final_gen["results"].get("reasoning", "No reasoning found"))
     logger.info("Chart Type: %s", final_gen["results"].get("chart_type", "Unknown"))
     logger.info("Chart Schema: %s", json.dumps(final_gen["results"].get("chart_schema", {}), indent=2))
    else:
     logger.error("Chart Generation Failed.")
        



# if __name__ == "__main__":
#     print("=== Starting Main Function ===")  # Debugging print
#     asyncio.run(main())

    
    # --- Chart Adjustment ---
    logger.info("=== Starting Chart Adjustment ===")
    original_schema = final_gen["results"]["chart_schema"]
    adjustment_option = ChartAdjustmentOption(
        chart_type="grouped_bar",
        x_axis="product_category_name",
        y_axis="total_sales",
        color="region_name"
    )
    adj_input = ChartAdjustmentInput(
        query="Convert the pie chart to a grouped bar chart comparing sales across regions",
        sql=api_result["code"],
        sample_data=sample_data,
        columns=columns,
        original_chart_schema={**original_schema,
                               "data": {"values": []}
                               },
        column_metadata=columns,
        adjustment_option=adjustment_option.model_dump()
    )
    
    adj_agent = ChartAdjustmentAgent(tokens_service=tokens_service, logger=logger)
    adj_result = await adj_agent.run(adj_input)
    logger.info("Chart adjustment received: %s", adj_result.data.model_dump_json(indent=2))#remove later



    logger.info("=== Restoring full dataset after adjustment ===")
    final_adj = post_processor.run(
        [adj_result.data.model_dump_json()],
        vega_schema,
        full_data,
        remove_data_from_chart_schema=False  # restore full data
    )
    if not final_adj:
        logger.error(" Adjustment did not return a valid schema.")
    else:    
        logger.info("Final adjusted chart schema: %s", final_adj["results"])#remove 


if __name__ == "__main__":
    print("=== Starting Main Function ===")  # Debugging
    asyncio.run(main())
