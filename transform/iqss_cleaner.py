"""
IQSS data transformation and cleaning module.

Cleans and normalizes IQSS (quality and safety indicators) data files.
"""
import logging
from pathlib import Path
from typing import Dict, Optional

import pandas as pd

from config import config

logger = logging.getLogger("healthtek.transform.iqss")


class IQSSTransformError(Exception):
    """Exception raised during IQSS transformation."""
    pass


def clean_iqss(
    filepath: str,
    annee: int,
    silver_dir: Optional[str] = None
) -> pd.DataFrame:
    """
    Clean and normalize IQSS data file.

    Business rules:
    - Normalize column names (lowercase, replace spaces with underscores)
    - Remove 'evolution' column if present
    - Convert nb_* columns to numeric
    - Convert score_* columns to float
    - Clean categorical columns: "1-Obligatoire" → "Obligatoire", "2-Facultatif" → "Facultatif"
    - Clean categorical columns: "1-Oui" → "Oui", "2-Non" → "Non"
    - Normalize FINESS identifier to 9 digits
    
    Args:
        filepath: Path to the raw IQSS file (CSV or Excel)
        annee: Year of the data
        silver_dir: Optional output directory (defaults to config.SILVER_DIR/iqss)
        
    Returns:
        Cleaned DataFrame
        
    Raises:
        IQSSTransformError: If transformation fails
        FileNotFoundError: If input file doesn't exist
    """
    logger.info(f"Starting IQSS cleaning for year {annee} from {filepath}")
    
    # Validate inputs
    input_path = Path(filepath)
    if not input_path.exists():
        raise FileNotFoundError(f"IQSS file not found: {filepath}")
    
    if not (2015 <= annee <= 2030):
        raise ValueError(f"Invalid year {annee}")

    try:
        # Load file based on extension
        ext = input_path.suffix.lower()
        
        if ext == ".csv":
            logger.debug("Loading CSV file")
            df = pd.read_csv(filepath, sep=";", dtype=str, encoding="latin-1")
        elif ext in [".xlsx", ".xls"]:
            logger.debug("Loading Excel file")
            df = pd.read_excel(filepath, dtype=str)
        else:
            raise IQSSTransformError(f"Unsupported file format: {ext}")
        
        logger.info(f"Loaded {len(df)} rows and {len(df.columns)} columns")
        
    except Exception as e:
        raise IQSSTransformError(f"Failed to load IQSS file: {e}") from e

    try:
        # Normalize column names
        df.columns = (
            df.columns
            .str.lower()
            .str.strip()
            .str.replace(" ", "_", regex=False)
            .str.replace("-", "_", regex=False)
        )
        logger.debug(f"Normalized {len(df.columns)} column names")

        # Remove evolution column if present
        if "evolution" in df.columns:
            df = df.drop(columns=["evolution"])
            logger.debug("Removed 'evolution' column")

        # Convert nb_* columns to numeric
        nb_cols = [c for c in df.columns if c.startswith("nb_")]
        for col in nb_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        logger.debug(f"Converted {len(nb_cols)} nb_* columns to numeric")

        # Convert score_* columns to float
        score_cols = [c for c in df.columns if c.startswith("score_")]
        for col in score_cols:
            df[col] = pd.to_numeric(df[col], errors="coerce")
        logger.debug(f"Converted {len(score_cols)} score_* columns to float")

        # Clean categorical columns with numbered prefixes
        # Handles patterns like "1-Obligatoire" → "Obligatoire", "2-Non" → "Non"
        categorical_cleaning_map = {
            "1-Obligatoire": "Obligatoire",
            "2-Facultatif": "Facultatif",
            "1-Oui": "Oui",
            "2-Non": "Non"
        }
        
        # Apply to known categorical columns
        categorical_columns = ["participation", "depot"]
        for col in categorical_columns:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .replace(categorical_cleaning_map)
                    .str.strip()
                )
                logger.debug(f"Cleaned '{col}' column")
        
        # Also check for any other columns that might have these patterns
        for col in df.columns:
            if col not in categorical_columns and df[col].dtype == 'object':
                # Check if column contains any of these patterns
                if df[col].isin(categorical_cleaning_map.keys()).any():
                    df[col] = df[col].replace(categorical_cleaning_map).str.strip()
                    logger.debug(f"Cleaned categorical values in column '{col}'")

        # Normalize FINESS identifier
        finess_candidates = ["finess", "nofinesset", "finess_etablissement"]
        for key in finess_candidates:
            if key in df.columns:
                df["finess"] = df[key].astype(str).str.zfill(9)
                logger.debug(f"Normalized FINESS from column '{key}'")
                break
        else:
            logger.warning("No FINESS column found in data")

        # Data quality checks
        logger.info("Running data quality checks")
        null_counts = df.isnull().sum()
        critical_nulls = null_counts[null_counts > len(df) * 0.5]
        
        if len(critical_nulls) > 0:
            logger.warning(f"Columns with >50% null values: {list(critical_nulls.index)}")

    except Exception as e:
        raise IQSSTransformError(f"Failed to transform IQSS data: {e}") from e

    # Save to silver directory
    try:
        if silver_dir:
            output_base = Path(silver_dir)
        else:
            output_base = config.get_silver_path("iqss")
        
        output_dir = output_base / str(annee)
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / f"resultats_iqss_{annee}.csv"
        df.to_csv(output_path, index=False, sep=";", encoding="utf-8-sig")
        
        logger.info(f"Saved cleaned data to {output_path}")
        logger.info(f"Final shape: {df.shape[0]} rows × {df.shape[1]} columns")
        
    except Exception as e:
        raise IQSSTransformError(f"Failed to save cleaned IQSS data: {e}") from e

    return df
