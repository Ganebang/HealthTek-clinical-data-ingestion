"""
FINESS data transformation and cleaning module.

Cleans and normalizes FINESS (healthcare facility registry) data files.
"""
import logging
from pathlib import Path
from typing import List, Optional

import pandas as pd

from config import config

logger = logging.getLogger("healthtek.transform.finess")


class FinessTransformError(Exception):
    """Exception raised during FINESS transformation."""
    pass


# Official FINESS establishment file header (32 columns)
# Source: https://www.data.gouv.fr/fr/datasets/finess-extraction-du-fichier-des-etablissements/
# Documentation: Description du jeu de données "établissements Géolocalisés"
FINESS_COLUMNS = [
    "structureet",          # Section name (always present, will be dropped)
    "nofinesset",           # Numéro FINESS ET
    "nofinessej",           # Numéro FINESS EJ
    "rs",                   # Raison sociale
    "rslongue",             # Raison sociale longue
    "complrs",              # Complément de raison sociale
    "compldistrib",         # Complément de distribution
    "numvoie",              # Numéro de voie
    "typvoie",              # Type de voie
    "voie",                 # Libellé de voie
    "compvoie",             # Complément de voie
    "lieuditbp",            # Lieu-dit / BP
    "commune",              # Code Commune
    "departement",          # Département
    "libdepartement",       # Libellé département
    "ligneacheminement",    # Code Postal + Lib commune
    "telephone",            # Téléphone
    "telecopie",            # Télécopie
    "categetab",            # Catégorie d'établissement
    "libcategetab",         # Libellé catégorie d'établissement
    "categagretab",         # Catégorie d'agrégat d'établissement
    "libcategagretab",      # Libellé catégorie d'agrégat d'établissement
    "siret",                # Numéro de SIRET
    "codeape",              # Code APE
    "codemft",              # Code MFT
    "libmft",               # Libellé MFT
    "codesph",              # Code SPH
    "libsph",               # Libellé SPH
    "dateouv",              # Date d'ouverture
    "dateautor",            # Date d'autorisation
    "datemaj",              # Date de mise à jour
    "numuai"                # Numéro éducation nationale
]


def clean_finess(
    filepath: str,
    silver_dir: Optional[str] = None
) -> pd.DataFrame:
    """
    Clean and normalize FINESS establishment data.

    Processing steps:
    - Apply official FINESS column header
    - Normalize column names
    - Filter for active establishments only (etat == 'A')
    - Clean and title-case text fields
    - Format SIRET to 14 digits
    - Create normalized 'finess' column from 'nofinesset'
    
    Args:
        filepath: Path to the raw FINESS file (CSV)
        silver_dir: Optional output directory (defaults to config.SILVER_DIR/finess)
        
    Returns:
        Cleaned DataFrame
        
    Raises:
        FinessTransformError: If transformation fails
        FileNotFoundError: If input file doesn't exist
    """
    logger.info(f"Starting FINESS cleaning from {filepath}")
    
    # Validate input
    input_path = Path(filepath)
    if not input_path.exists():
        raise FileNotFoundError(f"FINESS file not found: {filepath}")

    try:
        # Load raw FINESS file
        # Note: The raw file has a metadata header row (row 0) that needs to be skipped
        logger.debug("Loading FINESS CSV file")
        
        # Try multiple encodings
        encodings = ["utf-8", "latin1", "cp1252"]
        df = None
        
        for encoding in encodings:
            try:
                df = pd.read_csv(
                    filepath,
                    sep=";",
                    skiprows=1,  # Skip metadata header row
                    header=None,
                    dtype=str,
                    encoding=encoding
                )
                logger.info(f"Successfully loaded file with {encoding} encoding")
                break
            except UnicodeDecodeError:
                continue
                
        if df is None:
            raise FinessTransformError("Failed to decode file with supported encodings (utf-8, latin1, cp1252)")
        
        logger.debug(f"Loaded {len(df)} rows with {len(df.columns)} columns")
        
        # Validate column count matches expected (including structureet)
        if len(df.columns) != len(FINESS_COLUMNS):
            logger.warning(
                f"Column count mismatch: expected {len(FINESS_COLUMNS)}, "
                f"got {len(df.columns)}. Proceeding anyway."
            )
        
        #Apply official FINESS column headers (all 32 columns)
        df.columns = FINESS_COLUMNS[:len(df.columns)]
        
        # Drop the 'structureet' column (first column - contains section name)
        if 'structureet' in df.columns:
            df = df.drop(columns=['structureet'])
            logger.debug(f"Removed 'structureet' column, now {len(df.columns)} columns")
        
        logger.info(f"Loaded {len(df)} rows with {len(df.columns)} data columns")
        
    except Exception as e:
        raise FinessTransformError(f"Failed to load FINESS file: {e}") from e

    try:
        # Normalize column names
        df.columns = df.columns.str.lower().str.strip()
        logger.debug("Normalized column names")

        # Count before filtering
        total_rows = len(df)
        
        # Note: The current FINESS file structure (as of 2026) doesn't have a clear 'etat' column
        # with 'A'(Active)/'F'(Fermé) values. The structure has changed from the legacy format.
        # For now, we keep all establishments.
        logger.info(f"Loaded {total_rows} total establishments (not filtering by status)")
        
        # Legacy filter code (disabled until we understand new format):
        # if "etat" in df.columns:
        #     df = df[df["etat"] == "A"]
        #     logger.info(f"Filtered to {len(df)} active establishments (from {total_rows} total)")
        # else:
        #     logger.warning("'etat' column not found - skipping active filter")

        # Clean text columns
        text_cols = [
            "rs", "rslongue", "complrs", "compldistrib", 
            "libdepartement", "libcategetab", "libcategagretab", "libmft", "libsph"
        ]
        
        for col in text_cols:
            if col in df.columns:
                df[col] = (
                    df[col]
                    .astype(str)
                    .str.strip()
                    .str.title()
                    .str.replace("_", " ", regex=False)
                )
        logger.debug(f"Cleaned {len([c for c in text_cols if c in df.columns])} text columns")

        # Format SIRET to 14 digits
        if "siret" in df.columns:
            df["siret"] = df["siret"].astype(str).str.zfill(14)
            logger.debug("Formatted SIRET column")
        else:
            logger.warning("'siret' column not found")

        # Create normalized finess column
        if "nofinesset" in df.columns:
            df["finess"] = df["nofinesset"].astype(str).str.zfill(9)
            logger.debug("Created normalized 'finess' column")
        else:
            raise FinessTransformError("Required column 'nofinesset' not found")

        # Data quality checks
        logger.info("Running data quality checks")
        
        # Check for duplicates on FINESS identifier
        if "finess" in df.columns:
            duplicate_count = df["finess"].duplicated().sum()
            if duplicate_count > 0:
                logger.warning(f"Found {duplicate_count} duplicate FINESS identifiers")
        
        # Check for missing critical fields
        critical_fields = ["finess", "rs", "commune"]
        for field in critical_fields:
            if field in df.columns:
                null_count = df[field].isnull().sum()
                if null_count > 0:
                    logger.warning(f"Field '{field}' has {null_count} null values")

    except Exception as e:
        raise FinessTransformError(f"Failed to transform FINESS data: {e}") from e

    # Save to silver directory
    try:
        if silver_dir:
            output_dir = Path(silver_dir) / "finess"
        else:
            output_dir = config.get_silver_path("finess")
        
        output_dir.mkdir(parents=True, exist_ok=True)
        
        output_path = output_dir / "finess.csv"
        output_path = output_dir / "finess.csv"
        df.to_csv(output_path, index=False, sep=";", encoding="utf-8-sig")
        
        logger.info(f"Saved cleaned data to {output_path}")
        logger.info(f"Final shape: {df.shape[0]} rows × {df.shape[1]} columns")
        
    except Exception as e:
        raise FinessTransformError(f"Failed to save cleaned FINESS data: {e}") from e

    return df
