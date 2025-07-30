"""
Analytics Utils Package.
This package contains utility functions and models for Analytics PAL.
"""

from app.pal.analytics.utils.models import (
    Condition, 
    TimeRange, 
    QueryAnalysisResult,
    GeneratedCode,
    ColumnInfo,
    TableInfo,
    SchemaInfo, 
    DatabaseInfo,
    TableData,
    CodeGenerationResult,
    InsightGenerationResult,
    VisualizationSuggestion,
    ForeignKeyRelationship,
    SharedColumnRelationship,
    ColumnStatistics,
    TableRelationship,
    KeyMetric,
    InsightResult,
    NumericStats,
    CategoryStats,
    DataSummary
)

from app.pal.analytics.utils.prompts import (
    QUERY_ANALYZER_SYSTEM_PROMPT,
    QUERY_ANALYZER_PROMPT_TEMPLATE,
    CODE_GENERATOR_SYSTEM_PROMPT,
    CODE_GENERATOR_PROMPT_TEMPLATE,
    SQL_GENERATOR_SYSTEM_PROMPT,
    PYTHON_GENERATOR_SYSTEM_PROMPT,
    SQL_GENERATOR_PROMPT_TEMPLATE,
    PYTHON_GENERATOR_PROMPT_TEMPLATE,
    INSIGHT_GENERATOR_SYSTEM_PROMPT,
    INSIGHT_GENERATOR_PROMPT_TEMPLATE
)

__all__ = [
    # Models
    "Condition", 
    "TimeRange", 
    "QueryAnalysisResult",
    "GeneratedCode",
    "CodeGenerationResult",
    "InsightGenerationResult",
    "VisualizationSuggestion",
    "ColumnInfo",
    "TableInfo",
    "SchemaInfo", 
    "DatabaseInfo",
    "TableData",
    "ForeignKeyRelationship",
    "SharedColumnRelationship",
    "ColumnStatistics",
    "TableRelationship",
    "KeyMetric",
    "InsightResult",
    "NumericStats",
    "CategoryStats",
    "DataSummary",
    
    # Prompts
    "QUERY_ANALYZER_SYSTEM_PROMPT",
    "QUERY_ANALYZER_PROMPT_TEMPLATE",
    "CODE_GENERATOR_SYSTEM_PROMPT",
    "CODE_GENERATOR_PROMPT_TEMPLATE",
    "SQL_GENERATOR_SYSTEM_PROMPT",
    "PYTHON_GENERATOR_SYSTEM_PROMPT",
    "SQL_GENERATOR_PROMPT_TEMPLATE",
    "PYTHON_GENERATOR_PROMPT_TEMPLATE",
    "INSIGHT_GENERATOR_SYSTEM_PROMPT",
    "INSIGHT_GENERATOR_PROMPT_TEMPLATE"
] 