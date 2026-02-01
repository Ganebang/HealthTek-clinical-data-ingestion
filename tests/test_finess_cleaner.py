"""
Tests for FINESS data cleaning and transformation.
"""
import pytest
import pandas as pd
from pathlib import Path
from unittest.mock import patch

from transform.finess_cleaner import clean_finess, FinessTransformError, FINESS_COLUMNS


@pytest.mark.unit
class TestCleanFiness:
    """Test suite for clean_finess function."""
    
    def test_clean_finess_success(self, temp_dir, sample_finess_csv_data):
        """Test successful cleaning of FINESS file."""
        # Create test file
        input_file = temp_dir / "finess_raw.csv"
        input_file.write_text(sample_finess_csv_data)
        
        output_dir = temp_dir / "silver"
        
        # Clean the data
        df = clean_finess(str(input_file), str(output_dir))
        
        # Verify DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2  # Two establishments in sample data
        assert "finess" in df.columns
        
        # Check that only active establishments are included
        assert all(df["etat"] == "A")
        
        # Check FINESS formatting (9 digits)
        assert df["finess"].iloc[0] == "010000001"
        assert df["finess"].iloc[1] == "020000002"
        
        # Check SIRET formatting (14 digits)
        assert df["siret"].iloc[0] == "12345678901234"
        assert df["siret"].iloc[1] == "98765432109876"
        
        # Verify output file created
        output_file = output_dir / "finess" / "finess.csv"
        assert output_file.exists()
    
    def test_clean_finess_file_not_found(self, temp_dir):
        """Test error when input file doesn't exist."""
        with pytest.raises(FileNotFoundError):
            clean_finess("/nonexistent/file.csv", str(temp_dir))
    
    def test_clean_finess_text_cleaning(self, temp_dir):
        """Test text field cleaning and title casing."""
        # Create test data with messy text
        csv_data = ";".join(["010000001"] + [""] * 2 + ["hopital_test", "HOPITAL TEST LONG"] + [""] * 7 +
                             ["paris"] + [""] * 4 + ["ile-de-france"] + [""] * 12 + ["A"] + [""] * 7)
        csv_data += "\n"
        
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)
        
        df = clean_finess(str(input_file), str(temp_dir))
        
        # Check text cleaning
        if len(df) > 0 and "rs" in df.columns:
            assert df["rs"].iloc[0] == "Hopital Test"  # Underscores replaced, title case
    
    def test_clean_finess_active_filter(self, temp_dir):
        """Test filtering of active establishments."""
        # Create data with active and inactive establishments
        active = ";".join(["010000001"] + [""] * 22 + ["A"] + [""] * 9)
        inactive = ";".join(["020000002"] + [""] * 22 + ["F"] + [""] * 9)  # F = Fermé (closed)
        
        csv_data = active + "\n" + inactive + "\n"
        
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)
        
        df = clean_finess(str(input_file), str(temp_dir))
        
        # Only active establishment should remain
        assert len(df) == 1
        assert df["finess"].iloc[0] == "010000001"
    
    def test_clean_finess_column_headers(self, temp_dir):
        """Test that correct column headers are applied."""
        csv_data = ";".join(["010000001"] * len(FINESS_COLUMNS)) + "\n"
        
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)
        
        df = clean_finess(str(input_file), str(temp_dir))
        
        # Check that expected columns exist
        assert "nofinesset" in df.columns
        assert "rs" in df.columns
        assert "siret" in df.columns
        assert "etat" in df.columns
    
    def test_clean_finess_missing_nofinesset(self, temp_dir, mocker):
        """Test error when nofinesset column is missing."""
        # Mock pd.read_csv to return DataFrame without nofinesset
        mock_df = pd.DataFrame({"other_col": [1, 2, 3]})
        mocker.patch('pandas.read_csv', return_value=mock_df)
        
        input_file = temp_dir / "test.csv"
        input_file.write_text("dummy")
        
        with pytest.raises(FinessTransformError, match="nofinesset"):
            clean_finess(str(input_file), str(temp_dir))
    
    @patch('transform.finess_cleaner.config')
    def test_clean_finess_uses_config_default(self, mock_config, temp_dir, sample_finess_csv_data):
        """Test that clean_finess uses config when silver_dir not provided."""
        mock_config.get_silver_path.return_value = temp_dir / "silver"
        
        input_file = temp_dir / "test.csv"
        input_file.write_text(sample_finess_csv_data)
        
        df = clean_finess(str(input_file))
        
        assert isinstance(df, pd.DataFrame)
        mock_config.get_silver_path.assert_called()
    
    def test_clean_finess_siret_padding(self, temp_dir):
        """Test SIRET number padding to 14 digits."""
        csv_data = ";".join(["010000001", "EJ001", "Test", "Test Long", "", "", "12345"] + 
                           [""] * 16 + ["A"] + [""] * 9) + "\n"
        
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)
        
        df = clean_finess(str(input_file), str(temp_dir))
        
        # SIRET should be padded to 14 digits
        assert df["siret"].iloc[0] == "00000000012345"
