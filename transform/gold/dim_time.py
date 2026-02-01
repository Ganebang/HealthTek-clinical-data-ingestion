"""
Dimension: Time

Creates a time dimension for temporal analysis.

Provides a standardized date dimension with year, quarter, month attributes.
"""

import logging
from pathlib import Path
from typing import Any, Dict, Optional

import pandas as pd

logger = logging.getLogger("healthtek.gold.dim_time")


def create_dim_time(
    start_year: int = 2015, end_year: int = 2030, output_path: Optional[Path] = None
) -> Dict[str, Any]:
    """
    Create dim_time dimension table.

    Args:
        start_year: Starting year for time dimension
        end_year: Ending year for time dimension
        output_path: Path where dimension table will be saved

    Returns:
        Dictionary with transformation metrics
    """
    logger.info(f"Creating dim_time from {start_year} to {end_year}")

    # Generate date range
    dates = pd.date_range(start=f"{start_year}-01-01", end=f"{end_year}-12-31", freq="D")

    # Create dimension
    dim = pd.DataFrame({"date": dates})
    dim["year"] = dim["date"].dt.year
    dim["quarter"] = dim["date"].dt.quarter
    dim["month"] = dim["date"].dt.month
    dim["month_name"] = dim["date"].dt.strftime("%B")
    dim["day"] = dim["date"].dt.day
    dim["day_of_week"] = dim["date"].dt.dayofweek
    dim["day_name"] = dim["date"].dt.strftime("%A")
    dim["week"] = dim["date"].dt.isocalendar().week
    dim["is_weekend"] = dim["day_of_week"].isin([5, 6])

    # Add current year flag
    current_year = pd.Timestamp.now().year
    dim["is_current_year"] = dim["year"] == current_year

    # Add metadata
    dim["record_created_at"] = pd.Timestamp.now()

    # Save
    if output_path:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        dim.to_parquet(output_path, index=False, compression="snappy")
        file_size_mb = output_path.stat().st_size / (1024 * 1024)
        logger.info(f"Saved dim_time to {output_path} ({file_size_mb:.2f} MB)")
    else:
        file_size_mb = 0

    metrics = {
        "output_rows": len(dim),
        "start_year": start_year,
        "end_year": end_year,
        "file_size_mb": file_size_mb,
    }

    logger.info(f"Time dimension metrics: {metrics}")
    return metrics


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)

    gold_path = Path("data/gold/dimensions/dim_time.parquet")
    metrics = create_dim_time(output_path=gold_path)
    print("\n✅ dim_time created successfully!")
    print(f"   Date rows: {metrics['output_rows']:,}")
