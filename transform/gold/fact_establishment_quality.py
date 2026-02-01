"""
Fact: Establishment Quality

Creates the primary fact table joining FINESS establishments with IQSS quality indicators.

Grain: One row per establishment per year (from IQSS data)
"""

import logging
from pathlib import Path
from typing import Any, Dict

import numpy as np
import pandas as pd

logger = logging.getLogger("healthtek.gold.fact_establishment_quality")


def create_fact_establishment_quality(
    silver_finess_path: Path, silver_iqss_dir: Path, output_path: Path
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
    logger.info("Creating fact_establishment_quality")

    # Load all IQSS files (both CSV and XLSX)
    iqss_files = list(silver_iqss_dir.glob("*/resultats_iqss_*.*"))
    # Filter for valid extensions
    iqss_files = [f for f in iqss_files if f.suffix in [".csv", ".xlsx", ".xls"]]

    if not iqss_files:
        logger.warning(f"No IQSS files found in {silver_iqss_dir}")
        return {"output_rows": 0}

    logger.info(f"Found {len(iqss_files)} IQSS files")

    # Load and combine all IQSS data
    iqss_dfs = []
    for iqss_file in iqss_files:
        try:
            # Extract year from path (data/silver/iqss/2024/resultats_iqss_2024.csv)
            year = iqss_file.parent.name

            if iqss_file.suffix == ".csv":
                # handling encoding issues common in French govt data
                try:
                    df_year = pd.read_csv(
                        iqss_file, sep=";", encoding="utf-8", dtype={"finess": str}
                    )
                except UnicodeDecodeError:
                    df_year = pd.read_csv(
                        iqss_file, sep=";", encoding="latin1", dtype={"finess": str}
                    )
            else:
                df_year = pd.read_excel(iqss_file, dtype={"finess": str})

            df_year["year"] = int(year)
            iqss_dfs.append(df_year)
            logger.info(f"  Loaded {len(df_year)} records from year {year}")
        except Exception as e:
            logger.error(f"Failed to load {iqss_file}: {e}")
            continue

    df_iqss = pd.concat(iqss_dfs, ignore_index=True)
    logger.info(f"Combined IQSS data: {len(df_iqss):,} records")

    # Normalize column names (handle variations across years)
    # 2019-2024: 'score_all_ajust', 'score_ALL_ssr_ajust', 'score_all_ssr_ajust'
    score_cols = [
        c
        for c in df_iqss.columns
        if "score" in c.lower() and "all" in c.lower() and "ajust" in c.lower()
    ]
    logger.info(f"Found score columns: {score_cols}")

    # Create a standardized 'score_all_ssr_ajust' column if not exists
    # Coalesce score columns into 'score_all_ssr_ajust'
    # Priority: score_all_ssr_ajust > score_ALL_ssr_ajust > score_all_ajust
    candidates = ["score_all_ssr_ajust", "score_ALL_ssr_ajust", "score_all_ajust"]

    # Ensure target column exists
    if "score_all_ssr_ajust" not in df_iqss.columns:
        df_iqss["score_all_ssr_ajust"] = np.nan

    # Fill missing values from other candidates
    for col in candidates:
        if col in df_iqss.columns and col != "score_all_ssr_ajust":
            df_iqss["score_all_ssr_ajust"] = df_iqss["score_all_ssr_ajust"].fillna(df_iqss[col])
    # Fallback to finding any column with 'score' and 'all' if detailed logic failed
    if df_iqss["score_all_ssr_ajust"].isna().all():
        fallback = next((c for c in score_cols if "dp" not in c), None)
        if fallback:
            df_iqss["score_all_ssr_ajust"] = df_iqss["score_all_ssr_ajust"].fillna(
                df_iqss[fallback]
            )
        else:
            # Only warn if we really still have nothing
            if df_iqss["score_all_ssr_ajust"].isna().all():
                logger.warning(
                    "Could not find overall score column. Evolution metrics will be empty."
                )

    # --- Evolution Calculation Logic ---
    # Sort for window operations
    df_iqss = df_iqss.sort_values(["finess", "year"])

    # Get previous year's score
    # We group by finess and shift 1 to get the previous record
    # Then we verify if the previous record is actually year - 1
    df_iqss["prev_score"] = df_iqss.groupby("finess")["score_all_ssr_ajust"].shift(1)
    df_iqss["prev_year"] = df_iqss.groupby("finess")["year"].shift(1)

    # Calculate score difference only if previous year is exactly year - 1
    df_iqss["score_diff"] = None
    mask_consecutive = df_iqss["year"] == df_iqss["prev_year"] + 1

    # Ensure numeric conversion before subtraction
    score_current = pd.to_numeric(df_iqss["score_all_ssr_ajust"], errors="coerce")
    score_prev = pd.to_numeric(df_iqss["prev_score"], errors="coerce")

    df_iqss.loc[mask_consecutive, "score_diff"] = score_current - score_prev
    df_iqss.loc[mask_consecutive, "previous_score_val"] = score_prev

    # Custom Trend Logic (simplified business rule)
    def get_custom_trend(diff):
        if pd.isna(diff):
            return "N/A"
        if diff >= 1.0:
            return "Improvement"
        elif diff <= -1.0:
            return "Decline"
        else:
            return "Stable"

    df_iqss["evolution_custom_trend"] = df_iqss["score_diff"].apply(get_custom_trend)

    # Clean official evolution label (remove "3-", "2-", etc prefix)
    # e.g., "3-Amélioration" -> "Amélioration"
    def clean_evolution(val):
        if pd.isna(val):
            return None
        val = str(val)
        if "-" in val and val[0].isdigit():
            return val.split("-", 1)[1]
        return val

    df_iqss["evolution_clean"] = df_iqss["evolution"].apply(clean_evolution)

    # --- End Evolution Computation ---

    # Select and rename columns for fact table
    fact = pd.DataFrame()
    fact["finess"] = df_iqss["finess"]
    fact["year"] = df_iqss["year"]
    fact["region"] = df_iqss.get("region", None)
    fact["participation_status"] = df_iqss.get("participation", None)
    fact["data_submitted"] = df_iqss.get("depot", None)

    # Quality measures
    fact["overall_score"] = pd.to_numeric(df_iqss.get("score_all_ssr_ajust", None), errors="coerce")
    fact["welcome_score"] = pd.to_numeric(
        df_iqss.get("score_accueil_ssr_ajust", None), errors="coerce"
    )
    fact["care_score"] = pd.to_numeric(df_iqss.get("score_pec_ssr_ajust", None), errors="coerce")
    fact["facility_score"] = pd.to_numeric(
        df_iqss.get("score_lieu_ssr_ajust", None), errors="coerce"
    )
    fact["meal_score"] = pd.to_numeric(df_iqss.get("score_repas_ssr_ajust", None), errors="coerce")
    fact["discharge_score"] = pd.to_numeric(
        df_iqss.get("score_sortie_ssr_ajust", None), errors="coerce"
    )
    fact["recommendation_rate"] = pd.to_numeric(
        df_iqss.get("taux_reco_brut", None), errors="coerce"
    )
    fact["response_count"] = pd.to_numeric(
        df_iqss.get("nb_rep_score_all_ssr_ajust", None), errors="coerce"
    )

    # Evolution metrics
    fact["previous_overall_score"] = df_iqss.get("previous_score_val", None)
    fact["score_evolution_diff"] = df_iqss.get("score_diff", None)
    fact["evolution_label"] = df_iqss.get("evolution_clean", None)
    fact["evolution_custom_trend"] = df_iqss.get("evolution_custom_trend", None)

    # Flags
    fact["has_quality_data"] = fact["overall_score"].notna()

    # Add metadata
    fact["record_created_at"] = pd.Timestamp.now()

    # Save
    output_path.parent.mkdir(parents=True, exist_ok=True)
    fact.to_parquet(output_path, index=False, compression="snappy")
    file_size_mb = output_path.stat().st_size / (1024 * 1024)
    logger.info(f"Saved fact_establishment_quality to {output_path} ({file_size_mb:.2f} MB)")

    metrics = {
        "output_rows": len(fact),
        "unique_establishments": fact["finess"].nunique(),
        "years_covered": sorted(fact["year"].unique().tolist()),
        "records_with_scores": fact["has_quality_data"].sum(),
        "records_with_evolution": fact["score_evolution_diff"].notna().sum(),
        "file_size_mb": file_size_mb,
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
    print("\n✅ fact_establishment_quality created successfully!")
    print(f"   Total records: {metrics['output_rows']:,}")
    print(f"   Years: {metrics['years_covered']}")
