"""
Gold Layer Transformation Module

This module contains transformation logic for creating analytics-ready Gold layer tables
from Silver layer data. The Gold layer uses a dimensional model (star schema) optimized
for business intelligence and analytical queries.

Modules:
- dimensions: Dimension tables (establishments, geography, time, category)
- facts: Fact tables (establishment quality metrics)
- aggregates: Pre-computed aggregation tables
- utils: Shared utilities for Gold layer transformations
"""

__all__ = [
    "dim_establishment",
    "dim_geography",
    "dim_time",
    "dim_category",
    "fact_establishment_quality",
]
