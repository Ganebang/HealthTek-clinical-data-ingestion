"""
Tests for the DataSource base class.
"""


import pytest
import requests

from src.base import (
    DataSource,
    DataSourceError,
    DownloadError,
    RefreshCheckError,
    create_session_with_retries,
)


class ConcreteDataSource(DataSource):
    """Concrete implementation for testing."""

    def __init__(self, name: str, should_refresh_value: bool = True):
        super().__init__(name)
        self._should_refresh = should_refresh_value
        self.download_called = False

    def should_refresh(self) -> bool:
        return self._should_refresh

    def download(self) -> None:
        self.download_called = True


@pytest.mark.unit
class TestDataSource:
    """Test suite for DataSource base class."""

    def test_initialization(self):
        """Test DataSource initialization."""
        ds = ConcreteDataSource("test-source")
        assert ds.name == "test-source"
        assert ds.session is not None
        assert isinstance(ds.session, requests.Session)

    def test_run_with_refresh_needed(self, caplog):
        """Test run method when refresh is needed."""
        import logging

        caplog.set_level(logging.INFO)

        ds = ConcreteDataSource("test-source", should_refresh_value=True)
        ds.run()

        assert ds.download_called is True

    def test_run_without_refresh_needed(self, caplog):
        """Test run method when refresh is not needed."""
        import logging

        caplog.set_level(logging.INFO)

        ds = ConcreteDataSource("test-source", should_refresh_value=False)
        ds.run()

        assert ds.download_called is False

    def test_run_with_refresh_check_error(self):
        """Test run method when refresh check fails."""
        ds = ConcreteDataSource("test-source")

        def failing_should_refresh():
            raise RefreshCheckError("Test error")

        ds.should_refresh = failing_should_refresh

        with pytest.raises(RefreshCheckError):
            ds.run()

    def test_run_with_download_error(self):
        """Test run method when download fails."""
        ds = ConcreteDataSource("test-source", should_refresh_value=True)

        def failing_download():
            raise DownloadError("Download failed")

        ds.download = failing_download

        with pytest.raises(DownloadError):
            ds.run()

    def test_run_with_unexpected_error(self):
        """Test run method with unexpected error."""
        ds = ConcreteDataSource("test-source", should_refresh_value=True)

        def failing_download():
            raise ValueError("Unexpected error")

        ds.download = failing_download

        with pytest.raises(DataSourceError):
            ds.run()


@pytest.mark.unit
class TestCreateSessionWithRetries:
    """Test suite for create_session_with_retries function."""

    def test_creates_session(self):
        """Test that session is created."""
        session = create_session_with_retries()
        assert isinstance(session, requests.Session)

    def test_custom_parameters(self):
        """Test session creation with custom parameters."""
        session = create_session_with_retries(max_retries=5, backoff_factor=3.0, timeout=60)
        assert isinstance(session, requests.Session)
