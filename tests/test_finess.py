"""
Tests for FINESS data source.
"""

from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from src.base import DownloadError, RefreshCheckError
from src.finess import FinessSource


@pytest.mark.unit
class TestFinessSource:
    """Test suite for FinessSource class."""

    def test_initialization(self, temp_dir):
        """Test FinessSource initialization."""
        source = FinessSource(base_dir=str(temp_dir))
        assert source.name == "FINESS"
        assert source.base_dir == Path(temp_dir)
        assert source.meta_file == Path(temp_dir) / "last_modified.txt"

    def test_get_local_last_modified_no_file(self, temp_dir):
        """Test _get_local_last_modified when file doesn't exist."""
        source = FinessSource(base_dir=str(temp_dir))
        assert source._get_local_last_modified() is None

    def test_get_local_last_modified_with_file(self, temp_dir):
        """Test _get_local_last_modified when file exists."""
        source = FinessSource(base_dir=str(temp_dir))
        test_date = "2024-01-15T12:00:00"
        source.meta_file.write_text(test_date)
        assert source._get_local_last_modified() == test_date

    @patch("src.finess.config")
    def test_get_remote_last_modified_success(self, mock_config, temp_dir):
        """Test _get_remote_last_modified successful call."""
        mock_config.FINESS_API_URL = "https://example.com/finess"
        source = FinessSource(base_dir=str(temp_dir))

        mock_response = Mock()
        mock_response.json.return_value = {"last_modified": "2024-01-20T10:00:00"}
        mock_response.raise_for_status.return_value = None
        source.session.get = Mock(return_value=mock_response)

        result = source._get_remote_last_modified()
        assert result == "2024-01-20T10:00:00"

    @patch("src.finess.config")
    def test_get_remote_last_modified_failure(self, mock_config, temp_dir):
        """Test _get_remote_last_modified when API fails."""
        mock_config.FINESS_API_URL = "https://example.com/finess"
        source = FinessSource(base_dir=str(temp_dir))
        source.session.get = Mock(side_effect=Exception("API Error"))

        with pytest.raises(RefreshCheckError, match="Failed to fetch FINESS metadata"):
            source._get_remote_last_modified()

    @patch("src.finess.config")
    def test_should_refresh_different_dates(self, mock_config, temp_dir):
        """Test should_refresh when dates differ."""
        mock_config.FINESS_API_URL = "https://example.com/finess"
        source = FinessSource(base_dir=str(temp_dir))

        source.meta_file.write_text("2024-01-01T00:00:00")

        mock_response = Mock()
        mock_response.json.return_value = {"last_modified": "2024-01-15T12:00:00"}
        mock_response.raise_for_status.return_value = None
        source.session.get = Mock(return_value=mock_response)

        assert source.should_refresh() is True

    @patch("src.finess.config")
    def test_should_refresh_same_dates(self, mock_config, temp_dir):
        """Test should_refresh when dates are the same."""
        mock_config.FINESS_API_URL = "https://example.com/finess"
        source = FinessSource(base_dir=str(temp_dir))

        date = "2024-01-15T12:00:00"
        source.meta_file.write_text(date)

        mock_response = Mock()
        mock_response.json.return_value = {"last_modified": date}
        mock_response.raise_for_status.return_value = None
        source.session.get = Mock(return_value=mock_response)

        assert source.should_refresh() is False

    @patch("src.finess.config")
    def test_download_success(self, mock_config, temp_dir, sample_finess_api_response):
        """Test successful download."""
        mock_config.FINESS_API_URL = "https://example.com/finess"
        source = FinessSource(base_dir=str(temp_dir))

        mock_api_response = Mock()
        mock_api_response.json.return_value = sample_finess_api_response
        mock_api_response.raise_for_status.return_value = None

        mock_file_response = Mock()
        mock_file_response.content = b"test,finess,data"
        mock_file_response.raise_for_status.return_value = None

        source.session.get = Mock(side_effect=[mock_api_response, mock_file_response])

        source.download()

        assert (source.base_dir / "finess.csv").exists()
        assert source.meta_file.exists()
        assert source.meta_file.read_text() == "2024-01-15T12:00:00"

    @patch("src.finess.config")
    def test_download_no_matching_file(self, mock_config, temp_dir):
        """Test download when no matching file is found."""
        mock_config.FINESS_API_URL = "https://example.com/finess"
        source = FinessSource(base_dir=str(temp_dir))

        mock_response = Mock()
        mock_response.json.return_value = {
            "resources": [{"title": "Wrong file", "url": "https://example.com/wrong.csv"}]
        }
        mock_response.raise_for_status.return_value = None
        source.session.get = Mock(return_value=mock_response)

        with pytest.raises(DownloadError, match="No FINESS establishment file found"):
            source.download()
