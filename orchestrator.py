"""
Pipeline orchestrator for HealthTek clinical data ingestion.

Coordinates extraction and transformation of FINESS and IQSS data sources.
"""

import glob
import logging
import os
from typing import List, Optional

from config import config
from src.finess import FinessSource
from src.iqss import IQSSSource
from transform.finess_cleaner import clean_finess
from transform.iqss_cleaner import clean_iqss

logger = logging.getLogger("healthtek.orchestrator")


class PipelineError(Exception):
    """Exception raised when pipeline execution fails."""

    pass


class SimpleOrchestrator:
    """
    Orchestrates the ETL pipeline for clinical data ingestion.

    Manages extraction and transformation for both FINESS and IQSS data sources.
    """

    def __init__(self, bronze_dir: Optional[str] = None, silver_dir: Optional[str] = None):
        """
        Initialize the orchestrator.

        Args:
            bronze_dir: Directory for raw data (defaults to config.BRONZE_DIR)
            silver_dir: Directory for cleaned data (defaults to config.SILVER_DIR)
        """
        self.bronze = bronze_dir or config.BRONZE_DIR
        self.silver = silver_dir or config.SILVER_DIR

        # Ensure directories exist
        config.ensure_directories()

        logger.info(f"Initialized orchestrator - Bronze: {self.bronze}, Silver: {self.silver}")

    def run_finess(self) -> None:
        """
        Execute FINESS extraction and transformation.

        Raises:
            PipelineError: If FINESS pipeline fails
        """
        logger.info("=" * 60)
        logger.info("FINESS Pipeline Starting")
        logger.info("=" * 60)

        try:
            # Extraction
            logger.info("Step 1/2: Extracting FINESS data")
            finess_dir = os.path.join(self.bronze, "finess")
            src = FinessSource(base_dir=finess_dir)
            src.run()

            # Transformation
            logger.info("Step 2/2: Transforming FINESS data")
            finess_file = os.path.join(finess_dir, "finess.csv")

            if not os.path.exists(finess_file):
                raise PipelineError(f"FINESS file not found: {finess_file}")

            clean_finess(filepath=finess_file, silver_dir=self.silver)

            logger.info("FINESS pipeline completed successfully")

        except Exception as e:
            logger.error(f"FINESS pipeline failed: {e}")
            raise PipelineError(f"FINESS pipeline failed: {e}") from e

    def run_iqss(self, annees: List[int]) -> None:
        """
        Execute IQSS extraction and transformation for multiple years.

        Args:
            annees: List of years to process

        Raises:
            PipelineError: If IQSS pipeline fails for any year
        """
        logger.info("=" * 60)
        logger.info(f"IQSS Pipeline Starting for {len(annees)} years: {annees}")
        logger.info("=" * 60)

        successful_years = []
        failed_years = []

        for annee in annees:
            try:
                logger.info(f"\n{'=' * 60}")
                logger.info(f"Processing IQSS {annee}")
                logger.info(f"{'=' * 60}")

                # Extraction
                logger.info(f"Step 1/2: Extracting IQSS {annee}")
                iqss_dir = os.path.join(self.bronze, "iqss")
                src = IQSSSource(annee=annee, base_dir=iqss_dir)
                src.run()

                # Transformation
                logger.info(f"Step 2/2: Transforming IQSS {annee}")

                # Find the downloaded file
                year_folder = os.path.join(iqss_dir, str(annee))
                candidates = glob.glob(os.path.join(year_folder, "*.csv")) + glob.glob(
                    os.path.join(year_folder, "*.xlsx")
                )

                if not candidates:
                    raise FileNotFoundError(
                        f"No IQSS file found in {year_folder}. " f"Extraction may have failed."
                    )

                # Use the most recently modified file
                candidates.sort(key=os.path.getmtime, reverse=True)
                filepath = candidates[0]

                logger.info(f"Processing file: {filepath}")

                clean_iqss(
                    filepath=filepath, annee=annee, silver_dir=os.path.join(self.silver, "iqss")
                )

                successful_years.append(annee)
                logger.info(f"IQSS {annee} pipeline completed successfully")

            except Exception as e:
                logger.error(f"IQSS {annee} pipeline failed: {e}")
                failed_years.append(annee)
                # Continue with other years instead of failing completely
                continue

        # Summary
        logger.info("\n" + "=" * 60)
        logger.info("IQSS Pipeline Summary")
        logger.info("=" * 60)
        logger.info(f"Successful: {len(successful_years)} years - {successful_years}")
        logger.info(f"Failed: {len(failed_years)} years - {failed_years}")

        if failed_years:
            logger.warning(f"IQSS pipeline completed with failures for years: {failed_years}")

    def run(self, annees: List[int]) -> None:
        """
        Execute the complete ETL pipeline.

        Runs FINESS and IQSS pipelines sequentially.

        Args:
            annees: List of years to process for IQSS

        Raises:
            PipelineError: If pipeline execution fails
        """
        logger.info("\n" + "=" * 60)
        logger.info("HEALTHTEK DATA PIPELINE STARTING")
        logger.info("=" * 60)

        errors = []

        # Run FINESS pipeline
        try:
            self.run_finess()
        except PipelineError as e:
            logger.error(f"FINESS pipeline failed: {e}")
            errors.append(("FINESS", str(e)))

        # Run IQSS pipeline
        try:
            self.run_iqss(annees)
        except Exception as e:
            logger.error(f"IQSS pipeline failed: {e}")
            errors.append(("IQSS", str(e)))

        # Final summary
        logger.info("\n" + "=" * 60)
        logger.info("PIPELINE EXECUTION COMPLETE")
        logger.info("=" * 60)

        if errors:
            logger.error(f"Pipeline completed with {len(errors)} error(s)")
            for source, error in errors:
                logger.error(f"  - {source}: {error}")
        else:
            logger.info("All pipelines completed successfully!")
