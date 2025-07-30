# Chart Agent Prompts

This directory contains prompt templates used by the chart generation and adjustment agents.

## Structure

- `chart_prompts.py`: Contains prompts for chart generation and adjustment
  - `CHART_GENERATION_SYSTEM_PROMPT`: System prompt for the chart generation agent
  - `CHART_GENERATION_USER_PROMPT`: User prompt template for chart generation
  - `CHART_ADJUSTMENT_SYSTEM_PROMPT`: System prompt for the chart adjustment agent
  - `CHART_ADJUSTMENT_USER_PROMPT`: User prompt template for chart adjustment

## Usage

These prompts are imported and used by the corresponding agents in the parent directory. They provide instructions to the LLM models on how to generate or adjust chart schemas based on data and user queries.

## Design Principles

1. **Separation of concerns**: Keeping prompts separate from agent code makes them easier to update and maintain
2. **Consistency**: Following a similar structure to the Analytics PAL prompts for coherence across the codebase
3. **Clear instructions**: Each prompt contains detailed instructions for the specific task
4. **Structured output**: All prompts specify the expected output format as JSON structures

## Extending

When adding new chart-related agent types, follow this pattern:
1. Create new prompt constants in an appropriate file
2. Add them to the `__init__.py` exports
3. Document the purpose and format of each prompt 