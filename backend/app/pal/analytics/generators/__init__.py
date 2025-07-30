"""
Analytics Generators Package.
This package contains generators for analytics content.
"""

from app.pal.analytics.generators.recommendation_generator import (
    SchemaBasedRecommendationGenerator,
    RecommendationSuggestion
)

__all__ = [
    "SchemaBasedRecommendationGenerator",
    "RecommendationSuggestion"
] 