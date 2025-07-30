# Chart Generation Agents

This directory contains agents for chart generation and adjustment in the Analytics module.

## Components

- `chart_generation.py`: Contains the `ChartGenerationAgent` which analyzes data and generates appropriate chart schemas
- `chart_adjustment.py`: Contains the `ChartAdjustmentAgent` which adjusts existing chart schemas based on specified options
- `prompt/`: Contains prompt templates used by the chart agents

## Usage

These agents are used by the `ChartGenerationService` to create and adjust chart visualizations for analytics results. They utilize prompts from the `prompt` directory.

## Implementation

The agents use the Pydantic-AI Agent framework to interact with LLM models for intelligent chart creation. Each agent has:

1. Input models defining the expected input format
2. Result models defining the response structure
3. Prompt templates for the system and user prompts
4. Error handling and fallback mechanisms

## Data Flow

1. The `ChartService` receives a request to create or adjust a chart
2. It calls the `ChartGenerationService` with data, column metadata, and any query context
3. The generation service uses the appropriate agent to generate or adjust a chart schema
4. The result is processed and returned to the `ChartService` for storage and delivery 

## When everything is working
1. Remove the detailed logging of the input and output data
2. Remove the fallback mechanisms
3. Remove the detailed logging of the agent's internal state
4. Remove the check for the agent's initialization state
5. Remove the custom LLM call method
6. Remove the result type check
