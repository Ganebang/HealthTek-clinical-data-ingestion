"""
Dimension: Category

Creates an establishment category taxonomy dimension.

Transformations:
- Extracts unique category codes and labels
- Creates hierarchy with aggregate categories
- Derives sector classification (public/private) from legal status codes
"""

import logging
from pathlib import Path
from typing import Any, Dict

import pandas as pd

logger = logging.getLogger("healthtek.gold.dim_category")


def create_dim_category(silver_finess_path: Path, output_path: Path) -> Dict[str, Any]:
    """
    Create dim_category dimension table from Silver FINESS data.

    Args:
        silver_finess_path: Path to Silver FINESS CSV file
        output_path: Path where dimension table will be saved

    Returns:
        Dictionary with transformation metrics
    """
    logger.info(f"Creating dim_category from {silver_finess_path}")

    # Load Silver FINESS data
    df = pd.read_csv(silver_finess_path, sep=";", dtype=str, low_memory=False)
    logger.info(f"Loaded {len(df):,} records")

    # Extract category information
    cat_cols = ["categetab", "libcategetab", "categagretab", "libcategagretab", "codesph", "libsph"]
    df_cat = df[cat_cols].copy()

    # Create unique categories
    dim = (
        df_cat.groupby(["categetab", "libcategetab"], dropna=False)
        .agg(
            {
                "categagretab": "first",
                "libcategagretab": "first",
                "codesph": lambda x: x.mode()[0] if len(x.mode()) > 0 else None,
                "libsph": lambda x: x.mode()[0] if len(x.mode()) > 0 else None,
            }
        )
        .reset_index()
    )

    dim.columns = [
        "category_code",
        "category_label",
        "aggregate_code",
        "aggregate_label",
        "primary_legal_status_code",
        "primary_legal_status_label",
    ]

    # Derive sector from legal status
    # Status code 1 = Public, others typically private
    def derive_sector(status_code):
        if pd.isna(status_code):
            return "Unknown"
        try:
            if int(status_code) == 1:
                return "Public"
            else:
                return "Private"
        except (ValueError, TypeError):
            return "Unknown"

    dim["sector"] = dim["primary_legal_status_code"].apply(derive_sector)

    # Derive category type (broad classification)
    def categorize_type(label):
        if pd.isna(label):
            return "Unknown"
        label_lower = str(label).lower()
        if "pharmacie" in label_lower:
            return "Pharmacy"
        elif "hopital" in label_lower or "hospitalier" in label_lower:
            return "Hospital"
        elif "santé" in label_lower or "médical" in label_lower:
            return "Health Center"
        elif "personne" in label_lower and "âgé" in label_lower:
            return "Elderly Care"
        elif "laboratoire" in label_lower:
            return "Laboratory"
        else:
            return "Other"

    dim["category_type"] = dim["category_label"].apply(categorize_type)

    # Remove nulls
    dim = dim[dim["category_code"].notna()]

    # Sort by category code
    dim = dim.sort_values("category_code").reset_index(drop=True)

    # Add metadata
    dim["record_created_at"] = pd.Timestamp.now()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dim.to_parquet(output_path, index=False, compression="snappy")
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Saved dim_category to {output_path} ({file_size_mb:.2f} MB)")

    metrics = {
        "output_rows": len(dim),
        "unique_categories": dim["category_code"].nunique(),
        "public_categories": (dim["sector"] == "Public").sum(),
        "private_categories": (dim["sector"] == "Private").sum(),
        "file_size_mb": file_size_mb,
    }

    logger.info(f"Category dimension metrics: {metrics}")
    return metrics


if __name__ == "__main__":
    import sys

    logging.basicConfig(level=logging.INFO)

    silver_path = Path("data/silver/finess/finess.csv")
    gold_path = Path("data/gold/dimensions/dim_category.parquet")

    if not silver_path.exists():
        print(f"Error: Silver file not found: {silver_path}")
        sys.exit(1)

    metrics = create_dim_category(silver_path, gold_path)
    print("\n✅ dim_category created successfully!")
    print(f"   Unique categories: {metrics['unique_categories']:,}")
    print(f"   Public: {metrics['public_categories']}, Private: {metrics['private_categories']}")
