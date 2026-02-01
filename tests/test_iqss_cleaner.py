"""
Tests for IQSS data cleaning and transformation.
"""

from unittest.mock import patch

import pandas as pd
import pytest

from transform.iqss_cleaner import IQSSTransformError, clean_iqss


@pytest.mark.unit
class TestCleanIQSS:
    """Test suite for clean_iqss function."""

    def test_clean_iqss_csv_success(self, temp_dir, sample_iqss_csv_data):
        """Test successful cleaning of CSV file."""
        # Create test file
        input_file = temp_dir / "iqss_2023.csv"
        input_file.write_text(sample_iqss_csv_data)

        output_dir = temp_dir / "silver"

        # Clean the data
        df = clean_iqss(str(input_file), 2023, str(output_dir))

        # Verify DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 3
        assert "finess" in df.columns
        assert "evolution" not in df.columns  # Should be removed

        # Check column normalization
        assert "nb_sejours" in df.columns
        assert "score_global" in df.columns

        # Check FINESS formatting (should be 9 digits)
        assert df["finess"].iloc[0] == "010000001"

        # Check participation cleaning
        assert df["participation"].iloc[0] == "Obligatoire"
        assert df["participation"].iloc[1] == "Facultatif"

        # Verify output file created
        output_file = output_dir / "2023" / "resultats_iqss_2023.csv"
        assert output_file.exists()

    def test_clean_iqss_oui_non_cleaning(self, temp_dir):
        """Test cleaning of Oui/Non patterns."""
        csv_data = """finess;RS;depot
010000001;Hopital Test 1;1-Oui
020000002;Hopital Test 2;2-Non
030000003;Hopital Test 3;1-Oui
"""
        # Create test file
        input_file = temp_dir / "iqss_2023.csv"
        input_file.write_text(csv_data)

        output_dir = temp_dir / "silver"

        # Clean the data
        df = clean_iqss(str(input_file), 2023, str(output_dir))

        # Check depot cleaning (Oui/Non patterns)
        assert df["depot"].iloc[0] == "Oui"
        assert df["depot"].iloc[1] == "Non"
        assert df["depot"].iloc[2] == "Oui"

    def test_clean_iqss_file_not_found(self, temp_dir):
        """Test error when input file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            clean_iqss("/nonexistent/file.csv", 2023, str(temp_dir))

    def test_clean_iqss_invalid_year(self, temp_dir):
        """Test error with invalid year."""
        input_file = temp_dir / "test.csv"
        input_file.write_text("dummy,data\\n1,2")

        with pytest.raises(ValueError, match="Invalid year"):
            clean_iqss(str(input_file), 2010, str(temp_dir))

    def test_clean_iqss_unsupported_format(self, temp_dir):
        """Test error with unsupported file format."""
        input_file = temp_dir / "test.txt"
        input_file.write_text("dummy data")

        with pytest.raises(IQSSTransformError, match="Unsupported file format"):
            clean_iqss(str(input_file), 2023, str(temp_dir))

    def test_clean_iqss_numeric_conversion(self, temp_dir):
        """Test numeric column conversions."""
        csv_data = """finess;nb_sejours;nb_patients;score_qualite
010000001;100;50;85.5
020000002;invalid;60;90.0
030000003;300;70;invalid
"""
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)

        df = clean_iqss(str(input_file), 2023, str(temp_dir))

        # Check numeric conversions
        assert pd.api.types.is_numeric_dtype(df["nb_sejours"])
        assert pd.api.types.is_numeric_dtype(df["nb_patients"])
        assert pd.api.types.is_numeric_dtype(df["score_qualite"])

        # Check that invalid values became NaN
        assert pd.isna(df["nb_sejours"].iloc[1])
        assert pd.isna(df["score_qualite"].iloc[2])

    def test_clean_iqss_column_normalization(self, temp_dir):
        """Test column name normalization."""
        csv_data = """FINESS;RS ETABLISSEMENT;NB Sejours;Score-Global
010000001;Hospital;100;85.5
"""
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)

        df = clean_iqss(str(input_file), 2023, str(temp_dir))

        # Check normalized column names
        assert "finess" in df.columns
        assert "rs_etablissement" in df.columns
        assert "nb_sejours" in df.columns
        assert "score_global" in df.columns

    @patch("transform.iqss_cleaner.config")
    def test_clean_iqss_uses_config_default(self, mock_config, temp_dir, sample_iqss_csv_data):
        """Test that clean_iqss uses config when silver_dir not provided."""
        mock_config.get_silver_path.return_value = temp_dir / "silver"

        input_file = temp_dir / "test.csv"
        input_file.write_text(sample_iqss_csv_data)

        df = clean_iqss(str(input_file), 2023)

        assert isinstance(df, pd.DataFrame)
        mock_config.get_silver_path.assert_called()
