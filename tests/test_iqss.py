"""
Tests for IQSS data source.
"""
import pytest
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock
from datetime import datetime

from src.iqss import IQSSSource
from src.base import DownloadError


@pytest.mark.unit
class TestIQSSSource:
    """Test suite for IQSSSource class."""
    
    def test_initialization_valid_year(self, temp_dir):
        """Test initialization with valid year."""
        source = IQSSSource(annee=2023, base_dir=str(temp_dir))
        assert source.name == "IQSS-2023"
        assert source.annee == 2023
        assert source.base_dir == Path(temp_dir)
    
    def test_initialization_invalid_year(self):
        """Test initialization with invalid year."""
        with pytest.raises(ValueError, match="Invalid year"):
            IQSSSource(annee=2010)  # Too old
        
        with pytest.raises(ValueError, match="Invalid year"):
            IQSSSource(annee=2050)  # Too far in future
    
    def test_marker_file_property(self, temp_dir):
        """Test marker file property."""
        source = IQSSSource(annee=2023, base_dir=str(temp_dir))
        expected = temp_dir / "2023.done"
        assert source.marker_file == expected
    
    def test_year_directory_property(self, temp_dir):
        """Test year directory property."""
        source = IQSSSource(annee=2023, base_dir=str(temp_dir))
        expected = temp_dir / "2023"
        assert source.year_directory == expected
    
    def test_should_refresh_no_marker(self, temp_dir):
        """Test should_refresh when marker file doesn't exist."""
        source = IQSSSource(annee=2023, base_dir=str(temp_dir))
        assert source.should_refresh() is True
    
    def test_should_refresh_with_marker(self, temp_dir):
        """Test should_refresh when marker file exists."""
        source = IQSSSource(annee=2023, base_dir=str(temp_dir))
        source.marker_file.touch()
        assert source.should_refresh() is False
    
    @patch('src.iqss.config')
    def test_download_success(self, mock_config, temp_dir, mocker):
        """Test successful download."""
        mock_config.IQSS_API_URL_TEMPLATE = "https://example.com/iqss-{annee}/"
        
        source = IQSSSource(annee=2023, base_dir=str(temp_dir))
        
        # Mock API response with valid resource
        api_response_data = {
            "resources": [
                {
                    "title": "resultats iqss open-data 2023",
                    "url": "https://example.com/iqss_2023.csv"
                }
            ]
        }
        
        # Mock session responses
        mock_api_response = Mock()
        mock_api_response.json.return_value = api_response_data
        mock_api_response.raise_for_status.return_value = None
        
        mock_file_response = Mock()
        mock_file_response.content = b"test,data\n1,2"
        mock_file_response.raise_for_status.return_value = None
        
        source.session.get = Mock(side_effect=[mock_api_response, mock_file_response])
        
        # Execute download
        source.download()
        
        # Verify results
        assert source.marker_file.exists()
        assert (source.year_directory / "resultats_iqss_2023.csv").exists()
    
    @patch('src.iqss.config')
    def test_download_no_matching_file(self, mock_config, temp_dir, mocker):
        """Test download when no matching file is found."""
        mock_config.IQSS_API_URL_TEMPLATE = "https://example.com/iqss-{annee}/"
        
        source = IQSSSource(annee=2023, base_dir=str(temp_dir))
        
        # Mock API response with no matching resources
        mock_response = Mock()
        mock_response.json.return_value = {
            "resources": [
                {"title": "Wrong file", "url": "https://example.com/wrong.csv"}
            ]
        }
        mock_response.raise_for_status.return_value = None
        source.session.get = Mock(return_value=mock_response)
        
        # Should raise DownloadError
        with pytest.raises(DownloadError, match="No IQSS results file found"):
            source.download()
    
    @patch('src.iqss.config')
    def test_download_api_failure(self, mock_config, temp_dir):
        """Test download when API call fails."""
        mock_config.IQSS_API_URL_TEMPLATE = "https://example.com/iqss-{annee}/"
        
        source = IQSSSource(annee=2023, base_dir=str(temp_dir))
        
        # Mock failed API response
        source.session.get = Mock(side_effect=Exception("API Error"))
        
        with pytest.raises(DownloadError, match="Failed to fetch IQSS metadata"):
            source.download()
