"""
Pytest fixtures and configuration for tests.
"""
import json
import os
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

import pandas as pd
import pytest


@pytest.fixture
def temp_dir(tmp_path):
    """Provide a temporary directory for test files."""
    return tmp_path


@pytest.fixture
def bronze_dir(temp_dir):
    """Create a temporary bronze directory."""
    bronze = temp_dir / "bronze"
    bronze.mkdir(parents=True, exist_ok=True)
    return bronze


@pytest.fixture
def silver_dir(temp_dir):
    """Create a temporary silver directory."""
    silver = temp_dir / "silver"
    silver.mkdir(parents=True, exist_ok=True)
    return silver


@pytest.fixture
def mock_requests_session(mocker):
    """Mock requests.Session for API calls."""
    session = mocker.Mock()
    return session


@pytest.fixture
def sample_iqss_api_response() -> Dict[str, Any]:
    """Sample IQSS API response from data.gouv.fr."""
    return {
        "id": "test-dataset-id",
        "title": "IQSS 2023",
        "last_modified": "2023-12-01T10:00:00",
        "resources": [
            {
                "id": "resource-1",
                "title": "Resultats IQSS E-SATIS et CA-MCO OPEN DATA 2023",
                "url": "https://example.com/iqss_2023.csv",
                "format": "csv"
            },
            {
                "id": "resource-2",
                "title": "Other file",
                "url": "https://example.com/other.csv",
                "format": "csv"
            }
        ]
    }


@pytest.fixture
def sample_finess_api_response() -> Dict[str, Any]:
    """Sample FINESS API response from data.gouv.fr."""
    return {
        "id": "finess-test-id",
        "title": "FINESS Etablissements",
        "last_modified": "2024-01-15T12:00:00",
        "resources": [
            {
                "id": "finess-resource-1",
                "title": "FINESS Etablissements",
                "url": "https://example.com/finess.csv",
                "format": "csv"
            }
        ]
    }


@pytest.fixture
def sample_iqss_csv_data() -> str:
    """Sample IQSS CSV data."""
    return """finess;RS;NB_Sejours;Score_Global;Participation;Evolution
010000001;Hopital Test 1;150;85.5;1-Obligatoire;+2
020000002;Hopital Test 2;200;90.0;2-Facultatif;-1
030000003;Hopital Test 3;300;88.2;1-Obligatoire;0
"""


@pytest.fixture
def sample_iqss_dataframe() -> pd.DataFrame:
    """Sample IQSS DataFrame."""
    return pd.DataFrame({
        "finess": ["010000001", "020000002", "030000003"],
        "rs": ["Hopital Test 1", "Hopital Test 2", "Hopital Test 3"],
        "nb_sejours": [150, 200, 300],
        "score_global": [85.5, 90.0, 88.2],
        "participation": ["Obligatoire", "Facultatif", "Obligatoire"]
    })


@pytest.fixture
def sample_finess_csv_data() -> str:
    """Sample FINESS CSV data (headerless, pipe-separated)."""
    lines = [
        "010000001;EJ001;Hopital A;Hopital A - Nom Complet;355;106;12345678901234;10;RUE;PRINCIPALE;;;BP 123;Paris;75001;Ile-de-France;Paris;0101010101;0101010102;2.3456;48.8566;API_GPS;2024-01-01;A;2000-01-01;;1234A;MFT1;Medecine;SPH1;Public;APE1;Sante",
        "020000002;EJ002;Clinique B;Clinique B - Nom Complet;355;107;98765432109876;25;AVENUE;SECONDAIRE;;;;Lyon;69001;Rhone-Alpes;Rhone;0202020202;0202020203;4.8357;45.7640;API_GPS;2024-01-01;A;2005-01-01;;5678B;MFT2;Chirurgie;SPH2;Prive;APE2;Sante",
    ]
    return "\n".join(lines) + "\n"


@pytest.fixture
def sample_finess_dataframe() -> pd.DataFrame:
    """Sample cleaned FINESS DataFrame."""
    return pd.DataFrame({
        "nofinesset": ["010000001", "020000002"],
        "nofinessej": ["EJ001", "EJ002"],
        "rs": ["Hopital A", "Clinique B"],
        "rslongue": ["Hopital A - Nom Complet", "Clinique B - Nom Complet"],
        "siret": ["12345678901234", "98765432109876"],
        "commune": ["Paris", "Lyon"],
        "cpostal": ["75001", "69001"],
        "etat": ["A", "A"],
        "finess": ["010000001", "020000002"]
    })


@pytest.fixture
def mock_config(mocker, temp_dir):
    """Mock configuration module."""
    config_mock = mocker.Mock()
    config_mock.BRONZE_DIR = str(temp_dir / "bronze")
    config_mock.SILVER_DIR = str(temp_dir / "silver")
    config_mock.REQUEST_TIMEOUT = 30
    config_mock.MAX_RETRIES = 3
    config_mock.RETRY_BACKOFF_FACTOR = 2.0
    config_mock.LOG_LEVEL = "INFO"
    config_mock.FINESS_API_URL = "https://api.example.com/finess"
    config_mock.IQSS_API_URL_TEMPLATE = "https://api.example.com/iqss/{annee}"
    
    config_mock.get_bronze_path = lambda *parts: temp_dir / "bronze" / Path(*parts)
    config_mock.get_silver_path = lambda *parts: temp_dir / "silver" / Path(*parts)
    config_mock.ensure_directories = lambda: None
    
    return config_mock
