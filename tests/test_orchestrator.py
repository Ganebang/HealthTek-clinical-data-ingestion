"""
Integration tests for the orchestrator.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from orchestrator import PipelineError, SimpleOrchestrator


@pytest.mark.integration
class TestSimpleOrchestrator:
    """Integration tests for SimpleOrchestrator."""

    def test_initialization(self, temp_dir):
        """Test orchestrator initialization."""
        bronze = str(temp_dir / "bronze")
        silver = str(temp_dir / "silver")

        orch = SimpleOrchestrator(bronze_dir=bronze, silver_dir=silver)

        assert orch.bronze == bronze
        assert orch.silver == silver

    @patch("orchestrator.FinessSource")
    @patch("orchestrator.clean_finess")
    def test_run_finess_success(self, mock_clean, mock_source_class, temp_dir):
        """Test successful FINESS pipeline execution."""
        bronze = str(temp_dir / "bronze")
        silver = str(temp_dir / "silver")

        # Create the expected FINESS file
        finess_dir = Path(bronze) / "finess"
        finess_dir.mkdir(parents=True, exist_ok=True)
        (finess_dir / "finess.csv").write_text("dummy,data")

        # Mock the source
        mock_source = Mock()
        mock_source_class.return_value = mock_source

        orch = SimpleOrchestrator(bronze_dir=bronze, silver_dir=silver)
        orch.run_finess()

        # Verify source was created and run
        mock_source_class.assert_called_once()
        mock_source.run.assert_called_once()

        # Verify cleaner was called
        mock_clean.assert_called_once()

    @patch("orchestrator.FinessSource")
    def test_run_finess_missing_file(self, mock_source_class, temp_dir):
        """Test FINESS pipeline when file is missing."""
        bronze = str(temp_dir / "bronze")
        silver = str(temp_dir / "silver")

        mock_source = Mock()
        mock_source_class.return_value = mock_source

        orch = SimpleOrchestrator(bronze_dir=bronze, silver_dir=silver)

        with pytest.raises(PipelineError, match="FINESS file not found"):
            orch.run_finess()

    @patch("orchestrator.IQSSSource")
    @patch("orchestrator.clean_iqss")
    @patch("orchestrator.glob.glob")
    def test_run_iqss_success(self, mock_glob, mock_clean, mock_source_class, temp_dir):
        """Test successful IQSS pipeline execution."""
        bronze = str(temp_dir / "bronze")
        silver = str(temp_dir / "silver")

        # Create year directory and file
        year_dir = Path(bronze) / "iqss" / "2023"
        year_dir.mkdir(parents=True, exist_ok=True)
        test_file = year_dir / "resultats_iqss_2023.csv"
        test_file.write_text("dummy,iqss,data")

        # Mock glob to return our test file
        mock_glob.return_value = [str(test_file)]

        # Mock the source
        mock_source = Mock()
        mock_source_class.return_value = mock_source

        orch = SimpleOrchestrator(bronze_dir=bronze, silver_dir=silver)
        orch.run_iqss([2023])

        # Verify source was created and run
        mock_source_class.assert_called_once()
        mock_source.run.assert_called_once()

        # Verify cleaner was called
        mock_clean.assert_called_once()

    @patch("orchestrator.IQSSSource")
    @patch("orchestrator.clean_iqss")
    @patch("orchestrator.glob.glob")
    def test_run_iqss_multiple_years(self, mock_glob, mock_clean, mock_source_class, temp_dir):
        """Test IQSS pipeline with multiple years."""
        bronze = str(temp_dir / "bronze")
        silver = str(temp_dir / "silver")

        years = [2022, 2023]

        # Create files for both years
        for year in years:
            year_dir = Path(bronze) / "iqss" / str(year)
            year_dir.mkdir(parents=True, exist_ok=True)
            (year_dir / f"resultats_iqss_{year}.csv").write_text("data")

        # Mock glob to return appropriate files
        def glob_side_effect(pattern):
            if "2022" in pattern:
                return [str(Path(bronze) / "iqss" / "2022" / "resultats_iqss_2022.csv")]
            elif "2023" in pattern:
                return [str(Path(bronze) / "iqss" / "2023" / "resultats_iqss_2023.csv")]
            return []

        mock_glob.side_effect = glob_side_effect

        mock_source = Mock()
        mock_source_class.return_value = mock_source

        orch = SimpleOrchestrator(bronze_dir=bronze, silver_dir=silver)
        orch.run_iqss(years)

        # Verify source was created for each year
        assert mock_source_class.call_count == 2
        assert mock_clean.call_count == 2

    @patch("orchestrator.FinessSource")
    @patch("orchestrator.IQSSSource")
    @patch("orchestrator.clean_finess")
    @patch("orchestrator.clean_iqss")
    @patch("orchestrator.glob.glob")
    def test_run_full_pipeline(
        self,
        mock_glob,
        mock_clean_iqss,
        mock_clean_finess,
        mock_iqss_source,
        mock_finess_source,
        temp_dir,
    ):
        """Test full pipeline execution."""
        bronze = str(temp_dir / "bronze")
        silver = str(temp_dir / "silver")

        # Setup FINESS
        finess_dir = Path(bronze) / "finess"
        finess_dir.mkdir(parents=True, exist_ok=True)
        (finess_dir / "finess.csv").write_text("finess,data")

        # Setup IQSS
        year_dir = Path(bronze) / "iqss" / "2023"
        year_dir.mkdir(parents=True, exist_ok=True)
        iqss_file = year_dir / "resultats_iqss_2023.csv"
        iqss_file.write_text("iqss,data")

        mock_glob.return_value = [str(iqss_file)]

        orch = SimpleOrchestrator(bronze_dir=bronze, silver_dir=silver)
        orch.run([2023])

        # Verify both pipelines ran
        mock_finess_source.assert_called()
        mock_iqss_source.assert_called()
        mock_clean_finess.assert_called()
        mock_clean_iqss.assert_called()
