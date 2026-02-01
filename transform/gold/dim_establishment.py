"""
Dimension: Establishment

Creates a deduplicated, enriched master table of healthcare establishments.
This is the primary dimension table for the Gold layer.

Transformations:
- Deduplicates FINESS IDs (keeps most recent record)
- Enriches with derived flags (has_phone, has_fax, etc.)
- Standardizes missing values
- Creates normalized identifiers
"""

import logging
from pathlib import Path
from typing import Dict, Any

import pandas as pd

# Configure logging
logger = logging.getLogger("healthtek.gold.dim_establishment")


def create_dim_establishment(
    silver_finess_path: Path,
    output_path: Path
) -> Dict[str, Any]:
    """
    Create dim_establishment dimension table from Silver FINESS data.
    
    Args:
        silver_finess_path: Path to Silver FINESS CSV file
        output_path: Path where dimension table will be saved (Parquet)
    
    Returns:
        Dictionary with transformation metrics
    """
    logger.info(f"Creating dim_establishment from {silver_finess_path}")
    
    # Load Silver FINESS data
    df = pd.read_csv(silver_finess_path, sep=';', dtype=str, low_memory=False)
    initial_rows = len(df)
    logger.info(f"Loaded {initial_rows:,} records from Silver")
    
    # Sort by FINESS and update date (most recent first)
    df['datemaj'] = pd.to_datetime(df['datemaj'], errors='coerce')
    df = df.sort_values(['finess', 'datemaj'], ascending=[True, False])
    
    # Deduplicate - keep most recent record per FINESS
    df_dedup = df.drop_duplicates(subset=['finess'], keep='first')
    deduped_rows = len(df_dedup)
    duplicates_removed = initial_rows - deduped_rows
    logger.info(f"Deduplicated: {deduped_rows:,} unique establishments ({duplicates_removed:,} duplicates removed)")
    
    # Select and rename columns for dimension
    dim = pd.DataFrame()
    dim['finess'] = df_dedup['finess']
    dim['finess_entity'] = df_dedup['nofinessej']
    dim['name_short'] = df_dedup['rs']
    dim['name_long'] = df_dedup['rslongue']
    dim['category_code'] = df_dedup['categetab']
    dim['category_label'] = df_dedup['libcategetab']
    dim['aggregate_category_code'] = df_dedup['categagretab']
    dim['aggregate_category_label'] = df_dedup['libcategagretab']
    dim['siret'] = df_dedup['siret']
    dim['opening_date'] = pd.to_datetime(df_dedup['dateouv'], errors='coerce')
    dim['authorization_date'] = pd.to_datetime(df_dedup['dateautor'], errors='coerce')
    dim['last_update_date'] = df_dedup['datemaj']
    
    # Create enrichment flags
    dim['has_phone'] = df_dedup['telephone'].notna()
    dim['has_fax'] = df_dedup['telecopie'].notna()
    dim['has_siret'] = df_dedup['siret'].notna()
    dim['has_opening_date'] = dim['opening_date'].notna()
    
    # Standardize missing names
    dim['name_short'] = dim['name_short'].fillna('Unnamed Facility')
    dim['name_long'] = dim['name_long'].fillna(dim['name_short'])
    
    # Add data quality metadata
    dim['record_created_at'] = pd.Timestamp.now()
    
    # Data quality checks
    null_finess = dim['finess'].isna().sum()
    if null_finess > 0:
        logger.warning(f"Found {null_finess} records with null FINESS ID")
    
    # Save as Parquet (columnar format optimized for analytics)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    dim.to_parquet(output_path, index=False, compression='snappy')
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Saved dim_establishment to {output_path} ({file_size_mb:.2f} MB)")
    
    # Return metrics
    metrics = {
        'input_rows': initial_rows,
        'output_rows': len(dim),
        'duplicates_removed': duplicates_removed,
        'deduplication_rate': (duplicates_removed / initial_rows * 100) if initial_rows > 0 else 0,
        'columns': len(dim.columns),
        'file_size_mb': file_size_mb,
        'facilities_with_phone': dim['has_phone'].sum(),
        'facilities_with_siret': dim['has_siret'].sum(),
    }
    
    logger.info(f"Dimension metrics: {metrics}")
    return metrics


if __name__ == "__main__":
    # For testing
    import sys
    
    logging.basicConfig(level=logging.INFO)
    
    silver_path = Path("data/silver/finess/finess.csv")
    gold_path = Path("data/gold/dimensions/dim_establishment.parquet")
    
    if not silver_path.exists():
        print(f"Error: Silver file not found: {silver_path}")
        sys.exit(1)
    
    metrics = create_dim_establishment(silver_path, gold_path)
    print(f"\n✅ dim_establishment created successfully!")
    print(f"   Output rows: {metrics['output_rows']:,}")
    print(f"   Deduplication rate: {metrics['deduplication_rate']:.2f}%")
