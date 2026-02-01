"""
Dimension: Geography

Creates a geographic hierarchy dimension for rollup analysis.

Transformations:
- Extracts unique geographic locations from FINESS
- Parses postal code and city from ligneacheminement field
- Creates department -> region hierarchy
"""

import logging
import re
from pathlib import Path
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger("healthtek.gold.dim_geography")


def create_dim_geography(silver_finess_path: Path, output_path: Path) -> Dict[str, Any]:
    """
    Create dim_geography dimension table from Silver FINESS data.

    Args:
        silver_finess_path: Path to Silver FINESS CSV file
        output_path: Path where dimension table will be saved

    Returns:
        Dictionary with transformation metrics
    """
    logger.info(f"Creating dim_geography from {silver_finess_path}")

    # Load Silver FINESS data
    df = pd.read_csv(silver_finess_path, sep=";", dtype=str, low_memory=False)
    logger.info(f"Loaded {len(df):,} records")

    # Extract geographic columns
    geo_cols = ["departement", "libdepartement", "commune", "ligneacheminement"]
    df_geo = df[geo_cols + ["numvoie", "typvoie", "voie", "compvoie", "lieuditbp"]].copy()

    # Parse postal code and city from ligneacheminement
    # Format is typically: "75000 PARIS" or "01440 VIRIAT"
    def parse_postal_city(ligne):
        """
        Parse postal code and city from ligneacheminement field.

        Args:
            ligne: String in format "75000 PARIS" or "01440 VIRIAT"

        Returns:
            Tuple of (postal_code, city) or (None, ligne) if parsing fails
        """
        if pd.isna(ligne):
            return None, None
        match = re.match(r"^(\d{5})\s+(.+)$", str(ligne).strip())
        if match:
            return match.group(1), match.group(2)
        return None, ligne

    df_geo[["postal_code", "city"]] = df_geo["ligneacheminement"].apply(
        lambda x: pd.Series(parse_postal_city(x))
    )

    # Create unique geography records (by department)
    dim = (
        df_geo.groupby("departement", dropna=False)
        .agg(
            {
                "libdepartement": "first",
                "postal_code": lambda x: x.mode()[0] if len(x.mode()) > 0 else None,
                "city": lambda x: x.mode()[0] if len(x.mode()) > 0 else None,
                "commune": "first",
            }
        )
        .reset_index()
    )

    dim.columns = [
        "department_code",
        "department_name",
        "primary_postal_code",
        "primary_city",
        "primary_commune_code",
    ]

    # Add region mapping (simplified - you could enhance with official mapping)
    # For now, we'll infer from department name
    dim["region_name"] = dim["department_name"]  # Placeholder

    # Sort by department code
    dim = dim.sort_values("department_code").reset_index(drop=True)

    # Remove nulls
    dim = dim[dim["department_code"].notna()]

    # Add metadata
    dim["record_created_at"] = pd.Timestamp.now()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dim.to_parquet(output_path, index=False, compression="snappy")
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Saved dim_geography to {output_path} ({file_size_mb:.2f} MB)")

    metrics = {
        "output_rows": len(dim),
        "unique_departments": dim["department_code"].nunique(),
        "file_size_mb": file_size_mb,
    }

    logger.info(f"Geography dimension metrics: {metrics}")
    return metrics


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    silver_path = Path("data/silver/finess/finess.csv")
    gold_path = Path("data/gold/dimensions/dim_geography.parquet")

    if not silver_path.exists():
        print(f"Error: Silver file not found: {silver_path}")
        sys.exit(1)

    metrics = create_dim_geography(silver_path, gold_path)
    print("\n✅ dim_geography created successfully!")
    print(f"   Unique departments: {metrics['unique_departments']:,}")
