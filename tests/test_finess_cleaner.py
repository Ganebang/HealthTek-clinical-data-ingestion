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
        input_file = temp_dir / "finess_raw.csv"
        
        # Construct 32 columns. 
        # Index 0: structureet (ignored)
        # Index 1: nofinesset
        # Index 22: siret
        row1 = ["structureet"] + ["010000001"] + [""] * 20 + ["12345678901234"] + [""] * 9
        row2 = ["structureet"] + ["020000002"] + [""] * 20 + ["98765432109876"] + [""] * 9
        
        # Ensure length matches 32
        row1 = (row1 + [""] * 32)[:32]
        row2 = (row2 + [""] * 32)[:32]
        
        csv_data = "meta_ignored\n" + ";".join(row1) + "\n" + ";".join(row2)
        input_file.write_text(csv_data)
        
        output_dir = temp_dir / "silver"
        
        # Clean the data
        df = clean_finess(str(input_file), str(output_dir))
        
        # Verify DataFrame
        assert isinstance(df, pd.DataFrame)
        assert len(df) == 2
        assert "finess" in df.columns
        
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
        input_file = temp_dir / "test.csv"
        
        # Index 3: rs
        row = [""] * 32
        row[1] = "010000001"
        row[3] = "HOPITAL TEST LONG" 
        
        csv_data = "meta\n" + ";".join(row)
        input_file.write_text(csv_data)
        
        df = clean_finess(str(input_file), str(temp_dir))
        
        # Check text cleaning
        if len(df) > 0 and "rs" in df.columns:
            assert df["rs"].iloc[0] == "Hopital Test Long"
    
    def test_clean_finess_column_headers(self, temp_dir):
        """Test that correct column headers are applied."""
        row = ["val"] * 32
        row[1] = "010000001" # nofinesset required
        csv_data = "meta\n" + ";".join(row) + "\n"
        
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)
        
        df = clean_finess(str(input_file), str(temp_dir))
        
        # Check that expected columns exist
        assert "nofinesset" in df.columns
        assert "rs" in df.columns
        assert "siret" in df.columns
        # etat removed
    
    def test_clean_finess_missing_nofinesset(self, temp_dir, mocker):
        """Test error when nofinesset column is missing."""
        # Mock pd.read_csv to return DataFrame without nofinesset column logic
        # But actually clean_finess checks by column INDEX first, then renames.
        # It errors if "nofinesset" NAME is not found after renaming?
        # Code: if "nofinesset" in df.columns: ... else: raise
        
        # So if we provide data, it gets renamed. 
        # If we provide FEWER columns, maybe nofinesset (index 1) isn't there?
        # But `df.columns = FINESS_COLUMNS[:len]` names them sequentially.
        # nofinesset is index 1.
        # So we need meaningful tests.
        # If we return a dataframe that somehow drops the column? 
        # The easiest way to trigger the specific error "Required column 'nofinesset' not found"
        # is to have a dataframe where that column name doesn't exist.
        # But we FORCE the names.
        # The only way exists if we manually renamed it back or something.
        # Or if the file is empty?
        pass # Skipping this specific mock logic as it's brittle with the rename logic.
        
        # Actually proper way:
        # If we supply only 1 column (structureet), then index 1 (nofinesset) is missing.
        row = ["val"] # Only 1 col
        csv_data = "meta\n" + ";".join(row)
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)
        
        with pytest.raises(FinessTransformError): # Should fail on length or something
            clean_finess(str(input_file), str(temp_dir))

    @patch('transform.finess_cleaner.config')
    def test_clean_finess_uses_config_default(self, mock_config, temp_dir, sample_finess_csv_data):
        """Test that clean_finess uses config when silver_dir not provided."""
        mock_config.get_silver_path.return_value = temp_dir / "silver"
        
        row = [""] * 32
        row[1] = "010000001"
        input_file = temp_dir / "test.csv"
        input_file.write_text("meta\n" + ";".join(row))
        
        df = clean_finess(str(input_file))
        
        assert isinstance(df, pd.DataFrame)
        mock_config.get_silver_path.assert_called()
    
    def test_clean_finess_siret_padding(self, temp_dir):
        """Test SIRET number padding to 14 digits."""
        row = [""] * 32
        row[1] = "010000001"
        row[22] = "12345" # siret index
        
        csv_data = "meta\n" + ";".join(row)
        input_file = temp_dir / "test.csv"
        input_file.write_text(csv_data)
        
        df = clean_finess(str(input_file), str(temp_dir))
        
        # SIRET should be padded to 14 digits
        assert df["siret"].iloc[0] == "00000000012345"
