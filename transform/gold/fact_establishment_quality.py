"""
Fact: Establishment Quality

Creates the primary fact table joining FINESS establishments with IQSS quality indicators.

Grain: One row per establishment per year (from IQSS data)
"""

import logging
from pathlib import Path
from typing import Dict, Any
import glob

import pandas as pd

logger = logging.getLogger("healthtek.gold.fact_establishment_quality")


def create_fact_establishment_quality(
    silver_finess_path: Path,
    silver_iqss_dir: Path,
    output_path: Path
) -> Dict[str, Any]:
    """
    Create fact_establishment_quality from Silver FINESS and IQSS data.
    
    Args:
        silver_finess_path: Path to Silver FINESS CSV
        silver_iqss_dir: Directory containing IQSS CSV files by year
        output_path: Path where fact table will be saved
    
    Returns:
        Dictionary with transformation metrics
    """
    logger.info(f"Creating fact_establishment_quality")
    
    # Load all IQSS files
    iqss_files = list(silver_iqss_dir.glob('*/resultats_iqss_*.csv'))
    
    if not iqss_files:
        logger.warning(f"No IQSS files found in {silver_iqss_dir}")
        return {'output_rows': 0}
    
    logger.info(f"Found {len(iqss_files)} IQSS files")
    
    # Load and combine all IQSS data
    iqss_dfs = []
    for iqss_file in iqss_files:
        # Extract year from path (data/silver/iqss/2024/resultats_iqss_2024.csv)
        year = iqss_file.parent.name
        df_year = pd.read_csv(iqss_file, sep=';')
        df_year['year'] = int(year)
        iqss_dfs.append(df_year)
        logger.info(f"  Loaded {len(df_year)} records from year {year}")
    
    df_iqss = pd.concat(iqss_dfs, ignore_index=True)
    logger.info(f"Combined IQSS data: {len(df_iqss):,} records")
    
    # Select and rename columns for fact table
    fact = pd.DataFrame()
    fact['finess'] = df_iqss['finess']
    fact['year'] = df_iqss['year']
    fact['region'] = df_iqss.get('region', None)
    fact['participation_status'] = df_iqss.get('participation', None)
    fact['data_submitted'] = df_iqss.get('depot', None)
    
    # Quality measures
    fact['overall_score'] = pd.to_numeric(df_iqss.get('score_all_ssr_ajust', None), errors='coerce')
    fact['welcome_score'] = pd.to_numeric(df_iqss.get('score_accueil_ssr_ajust', None), errors='coerce')
    fact['care_score'] = pd.to_numeric(df_iqss.get('score_pec_ssr_ajust', None), errors='coerce')
    fact['facility_score'] = pd.to_numeric(df_iqss.get('score_lieu_ssr_ajust', None), errors='coerce')
    fact['meal_score'] = pd.to_numeric(df_iqss.get('score_repas_ssr_ajust', None), errors='coerce')
    fact['discharge_score'] = pd.to_numeric(df_iqss.get('score_sortie_ssr_ajust', None), errors='coerce')
    fact['recommendation_rate'] = pd.to_numeric(df_iqss.get('taux_reco_brut', None), errors='coerce')
    fact['response_count'] = pd.to_numeric(df_iqss.get('nb_rep_score_all_ssr_ajust', None), errors='coerce')
    
    # Flags
    fact['has_quality_data'] = fact['overall_score'].notna()
    
    # Add metadata
    fact['record_created_at'] = pd.Timestamp.now()
    
    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fact.to_parquet(output_path, index=False, compression='snappy')
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Saved fact_establishment_quality to {output_path} ({file_size_mb:.2f} MB)")
    
    metrics = {
        'output_rows': len(fact),
        'unique_establishments': fact['finess'].nunique(),
        'years_covered': sorted(fact['year'].unique().tolist()),
        'records_with_scores': fact['has_quality_data'].sum(),
        'file_size_mb': file_size_mb
    }
    
    logger.info(f"Fact table metrics: {metrics}")
    return metrics


if __name__ == "__main__":
    import sys
    logging.basicConfig(level=logging.INFO)
    
    finess_path = Path("data/silver/finess/finess.csv")
    iqss_dir = Path("data/silver/iqss")
    gold_path = Path("data/gold/facts/fact_establishment_quality.parquet")
    
    if not finess_path.exists():
        print(f"Error: FINESS file not found: {finess_path}")
        sys.exit(1)
    
    metrics = create_fact_establishment_quality(finess_path, iqss_dir, gold_path)
    print(f"\n✅ fact_establishment_quality created successfully!")
    print(f"   Total records: {metrics['output_rows']:,}")
    print(f"   Years: {metrics['years_covered']}")
