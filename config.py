"""
Configuration module for HealthTek Clinical Data Ingestion.

Loads configuration from environment variables with sensible defaults.
"""

import os
from pathlib import Path

from dotenv import load_dotenv

# Load environment variables from .env file if it exists
load_dotenv()


class Config:
    """Application configuration loaded from environment variables."""

    # Base directories
    BASE_DIR: Path = Path(__file__).parent
    BRONZE_DIR: str = os.getenv("BRONZE_DIR", "data/bronze")
    SILVER_DIR: str = os.getenv("SILVER_DIR", "data/silver")

    # API Configuration
    REQUEST_TIMEOUT: int = int(os.getenv("REQUEST_TIMEOUT", "30"))
    MAX_RETRIES: int = int(os.getenv("MAX_RETRIES", "3"))
    RETRY_BACKOFF_FACTOR: float = float(os.getenv("RETRY_BACKOFF_FACTOR", "2.0"))

    # Logging
    LOG_LEVEL: str = os.getenv("LOG_LEVEL", "INFO")
    LOG_FORMAT: str = os.getenv(
        "LOG_FORMAT", "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    )

    # Data Source URLs
    FINESS_DATASET_ID: str = "finess-extraction-du-fichier-des-etablissements"
    FINESS_API_URL: str = f"https://www.data.gouv.fr/api/1/datasets/{FINESS_DATASET_ID}/"

    IQSS_API_URL_TEMPLATE: str = (
        "https://www.data.gouv.fr/api/1/datasets/"
        "indicateurs-de-qualite-et-de-securite-des-soins-recueil-{annee}/"
    )

    @classmethod
    def get_bronze_path(cls, *parts: str) -> Path:
        """Get a path relative to the bronze directory."""
        return cls.BASE_DIR / cls.BRONZE_DIR / Path(*parts)

    @classmethod
    def get_silver_path(cls, *parts: str) -> Path:
        """Get a path relative to the silver directory."""
        return cls.BASE_DIR / cls.SILVER_DIR / Path(*parts)

    @classmethod
    def ensure_directories(cls) -> None:
        """Ensure data directories exist."""
        cls.get_bronze_path().mkdir(parents=True, exist_ok=True)
        cls.get_silver_path().mkdir(parents=True, exist_ok=True)


# Singleton instance
config = Config()
