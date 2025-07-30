"""
Chart Prompts package.
This package contains prompt templates for chart generation agents.
"""

from app.analytics.agents.chart.prompt.chart_prompts import (
    CHART_GENERATION_SYSTEM_PROMPT,
    CHART_GENERATION_USER_PROMPT,
    CHART_ADJUSTMENT_SYSTEM_PROMPT,
    CHART_ADJUSTMENT_USER_PROMPT
)

__all__ = [
    'CHART_GENERATION_SYSTEM_PROMPT',
    'CHART_GENERATION_USER_PROMPT',
    'CHART_ADJUSTMENT_SYSTEM_PROMPT',
    'CHART_ADJUSTMENT_USER_PROMPT'
] 